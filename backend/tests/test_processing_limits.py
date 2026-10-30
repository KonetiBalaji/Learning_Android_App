import multiprocessing


def allocation_probe(pipe):
    from study import memory_limits
    memory_limits.PARSER_MEMORY_BYTES = 128 * 1024 * 1024
    try:
        memory_limits.apply_parser_memory_limit()
        try:
            allocation = bytearray(256 * 1024 * 1024)
        except MemoryError:
            pipe.send("bounded")
        else:
            pipe.send("unbounded")
            del allocation
    except Exception:
        pipe.send("guard_unavailable")
    finally:
        pipe.close()


def test_parser_memory_guard_rejects_allocation_in_disposable_worker():
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=allocation_probe, args=(child,), daemon=True)
    process.start()
    child.close()
    try:
        assert parent.poll(20), "Memory guard probe did not finish"
        assert parent.recv() == "bounded"
    finally:
        parent.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=2)
