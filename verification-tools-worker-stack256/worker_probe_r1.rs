use std::ffi::c_void;

#[repr(C)]
#[derive(Clone, Copy)]
struct Limit { cur: u64, max: u64 }

extern "C" {
    fn getrlimit(which: i32, value: *mut Limit) -> i32;
    fn pthread_self() -> *mut c_void;
    fn pthread_get_stacksize_np(thread: *mut c_void) -> usize;
}

fn main() {
    const REQUEST: usize = 268_435_456;
    let mut before = Limit { cur: 0, max: 0 };
    assert_eq!(unsafe { getrlimit(3, &mut before) }, 0);
    let attempt = std::thread::Builder::new().name("stack-resource-probe".into())
        .stack_size(REQUEST).spawn(|| unsafe { pthread_get_stacksize_np(pthread_self()) });
    let size = match attempt {
        Ok(thread) => thread.join().expect("harmless worker join failed"),
        Err(error) => {
            println!("{{\"created\":false,\"requested_stack_bytes\":{},\"error\":{:?}}}", REQUEST, error.to_string());
            std::process::exit(1);
        }
    };
    let mut after = Limit { cur: 0, max: 0 };
    assert_eq!(unsafe { getrlimit(3, &mut after) }, 0);
    assert_eq!((before.cur, before.max), (after.cur, after.max));
    assert!(size >= REQUEST, "OS reported a smaller stack than requested");
    println!("{{\"created\":true,\"requested_stack_bytes\":{},\"os_reported_pthread_stack_bytes\":{},\"main_rlimit_before\":[{},{}],\"main_rlimit_after\":[{},{}],\"main_limits_unchanged\":true,\"proof_or_checker_execution\":false,\"scope\":\"one harmless worker; OS-reported stack reservation, not committed memory or proof success\"}}",
             REQUEST, size, before.cur, before.max, after.cur, after.max);
}
