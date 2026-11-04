import Lean

/-!
Separate-runtime named-theorem axiom probe for the external ETH replication campaign.

The probe is elaborated with trusted Lean imports only. Audited modules are named by command-line
arguments and imported at runtime with extensions disabled and private data loaded. It does not
import audited source while its own syntax is elaborated and does not enable initializers.

This is redundant axiom inspection, not a replacement for official Comparator statement comparison
or `leanchecker --fresh`. It trusts the pinned Lean compiler/runtime and native import machinery.

Run with the audited package's exact Lean toolchain and Lake environment:
  lake env lean --run /absolute/path/AuditTargets.lean Module TargetName [TargetName ...]
-/

open Lean

namespace EthReplicationAudit

def permitted : Array Name := #[`propext, `Quot.sound, `Classical.choice]

structure AuditState where
  visited : NameSet := {}
  axioms : NameSet := {}

abbrev AuditM := StateT AuditState IO

partial def walk (env : Environment) (name : Name) : AuditM Unit := do
  if (← get).visited.contains name then
    return
  modify fun s => { s with visited := s.visited.insert name }
  let some info := env.find? name
    | throw <| IO.userError s!"missing transitive dependency: {name}"
  if info.isUnsafe || info.isPartial then
    throw <| IO.userError s!"unsafe or partial constant in target dependency graph: {name}"
  let walkExpr (e : Expr) : AuditM Unit := e.getUsedConstants.forM (walk env)
  match info with
  | .axiomInfo v =>
      modify fun s => { s with axioms := s.axioms.insert name }
      walkExpr v.type
  | .defnInfo v => walkExpr v.type; walkExpr v.value
  | .thmInfo v => walkExpr v.type; walkExpr v.value
  | .opaqueInfo v => walkExpr v.type; walkExpr v.value
  | .ctorInfo v => walkExpr v.type
  | .recInfo v => walkExpr v.type
  | .inductInfo v => walkExpr v.type; v.ctors.forM (walk env)
  | .quotInfo _ => pure ()

def sortedNames (s : NameSet) : Array Name := s.toArray.qsort Name.lt

def checkStandardAxiom (trusted actual : Environment) (name : Name) : IO Unit := do
  let some (.axiomInfo original) := trusted.find? name
    | throw <| IO.userError s!"trusted Init lacks expected axiom declaration: {name}"
  let some (.axiomInfo observed) := actual.find? name
    | throw <| IO.userError s!"audited environment lacks expected axiom declaration: {name}"
  unless original.type == observed.type && original.levelParams == observed.levelParams do
    throw <| IO.userError s!"standard axiom signature differs from trusted Init: {name}"

def emit (value : Json) : IO Unit := do
  let out ← IO.getStdout
  out.putStrLn value.compress
  out.flush

def audit (moduleName : Name) (targetNames : Array Name) : IO UInt32 := do
  if ← isInitializerExecutionEnabled then
    throw <| IO.userError "initializer execution is unexpectedly enabled before audited import"
  initSearchPath (← findSysroot)
  let trusted ← importModules #[{ module := `Init }] {} (loadExts := false)
    (level := OLeanLevel.private)
  let env ← importModules #[{ module := moduleName }] {} (loadExts := false)
    (level := OLeanLevel.private)
  if ← isInitializerExecutionEnabled then
    throw <| IO.userError "initializer execution unexpectedly enabled after audited import"
  for axiomName in permitted do
    checkStandardAxiom trusted env axiomName
  emit <| Json.mkObj [
    ("schema", toJson "eth-target-axiom-audit/1"),
    ("event", toJson "environment"),
    ("module", toJson moduleName.toString),
    ("load_extensions", toJson false),
    ("load_level", toJson "private"),
    ("initializer_execution_enabled", toJson (← isInitializerExecutionEnabled)),
    ("standard_axiom_signature_check", toJson true),
    ("permitted_axioms", toJson (permitted.map (·.toString)))]
  let mut accepted := true
  for targetName in targetNames do
    let some (.thmInfo _) := env.find? targetName
      | throw <| IO.userError s!"requested target is missing or is not a theorem: {targetName}"
    let (_, state) ← (walk env targetName).run {}
    let axioms := sortedNames state.axioms
    let disallowed := axioms.filter fun ax => !permitted.contains ax
    let passed := disallowed.isEmpty
    accepted := accepted && passed
    emit <| Json.mkObj [
      ("schema", toJson "eth-target-axiom-audit/1"),
      ("event", toJson "target"),
      ("module", toJson moduleName.toString),
      ("target", toJson targetName.toString),
      ("visited_constants", toJson state.visited.toArray.size),
      ("axioms", toJson (axioms.map (·.toString))),
      ("disallowed_axioms", toJson (disallowed.map (·.toString))),
      ("passed", toJson passed)]
  emit <| Json.mkObj [
    ("schema", toJson "eth-target-axiom-audit/1"),
    ("event", toJson "complete"),
    ("module", toJson moduleName.toString),
    ("targets_checked", toJson targetNames.size),
    ("passed", toJson accepted),
    ("scope", toJson "named-theorem transitive axiom audit; no statement comparison or kernel replay")]
  return if accepted then 0 else 1

end EthReplicationAudit

def main (args : List String) : IO UInt32 := do
  try
    match args with
    | moduleArg :: firstTarget :: moreTargets =>
        let targetNames := (firstTarget :: moreTargets).toArray.map String.toName
        EthReplicationAudit.audit moduleArg.toName targetNames
    | _ =>
        IO.eprintln "usage: AuditTargets.lean Module TargetName [TargetName ...]"
        return 2
  catch ex =>
    EthReplicationAudit.emit <| Json.mkObj [
      ("schema", toJson "eth-target-axiom-audit/1"),
      ("event", toJson "error"),
      ("passed", toJson false),
      ("message", toJson ex.toString)]
    return 2
