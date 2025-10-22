import glob, yaml

def test_specs_loadable():
    for spec in glob.glob("openspec/specs/*.yml"):
        with open(spec, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert "feature" in data and "scenarios" in data and "assertions" in data
