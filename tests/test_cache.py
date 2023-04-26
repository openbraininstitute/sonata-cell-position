import app.cache as test_module


def test_check_cache(tmp_path, monkeypatch, input_path):
    # patch SAMPLING_RATIO to use the cache even with sampling_ratio higher than 0.01
    monkeypatch.setattr(test_module, "SAMPLING_RATIO", 0.5)
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    # write the cache
    result1 = test_module.check_cache(
        test_module.CacheParams(
            input_path=input_path,
            population_name="default",
            sampling_ratio=0.5,
            seed=102,
        )
    )
    assert isinstance(result1, test_module.CacheParams)
    assert result1.sampling_ratio == 1  # sampling_ratio / SAMPLING_RATIO
    path1 = result1.input_path
    assert path1.is_file()
    mtime1 = path1.stat().st_mtime_ns

    # read the cache
    result2 = test_module.check_cache(
        test_module.CacheParams(
            input_path=input_path,
            population_name="default",
            sampling_ratio=0.1,
            seed=102,
        )
    )
    assert isinstance(result2, test_module.CacheParams)
    assert result2.sampling_ratio == 0.2  # sampling_ratio / SAMPLING_RATIO
    path2 = result2.input_path
    assert path2.is_file()
    mtime2 = path2.stat().st_mtime_ns

    assert path1 == path2, "The cache has not been reused"
    assert mtime1 == mtime2, "The cache has been rewritten"


def test_check_cache_not_used(tmp_path, input_path):
    # cache not used because sampling_ratio is too high
    params = test_module.CacheParams(
        input_path=input_path,
        population_name="default",
        sampling_ratio=0.8,
        seed=102,
    )
    result = test_module.check_cache(params)
    assert result is params
