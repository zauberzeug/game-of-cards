"""Reproduce: the OpenClaw skill porter leaves an empty orphan subdir when a
nested source sibling is removed, and `drifted_skills()` does not flag it.

Exits 0 when the defect is FIXED:
  - re-porting after removing a nested source sibling subdir leaves NO empty
    orphan dir under openclaw-plugin/skills/<skill>/, and
  - drifted_skills() FLAGS the orphan while one remains, and
  - removing only one file from a still-populated subdir leaves it intact.

Exits 1 (defect present) when the empty orphan subdir lingers after re-port
or when drifted_skills() stays blind to it.

The script copies the porter's source/dst dirs into a temp sandbox so it never
mutates the real tree, then drives the porter against the sandbox.
"""
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()


def _load_porter(src_dir: Path, dst_dir: Path):
    """Load the porter module fresh with SRC_DIR/DST_DIR redirected to sandbox."""
    spec = importlib.util.spec_from_file_location(
        "porter_under_test", ROOT / "scripts" / "port_skills_to_openclaw.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.SRC_DIR = src_dir
    mod.DST_DIR = dst_dir
    # main()'s progress prints call ROOT-relative; keep them in-sandbox.
    mod.ROOT = src_dir.parent
    return mod


def main() -> int:
    real_src = ROOT / "goc" / "templates" / "skills"
    real_dst = ROOT / "openclaw-plugin" / "skills"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / "src"
        dst = tmp / "dst"
        shutil.copytree(real_src, src)
        shutil.copytree(real_dst, dst)

        # Pick a portable skill dir to attach a nested asset subdir to.
        porter = _load_porter(src, dst)
        portable = porter._portable_skill_dirs()
        skill = portable[0]
        skill_name = skill.name

        # Seed a nested sibling: <skill>/extra/asset.txt plus a sibling kept-dir
        # with two files (to prove we only prune the emptied one).
        (skill / "extra").mkdir()
        (skill / "extra" / "asset.txt").write_text("nested asset\n", encoding="utf-8")
        (skill / "kept").mkdir()
        (skill / "kept" / "a.txt").write_text("a\n", encoding="utf-8")
        (skill / "kept" / "b.txt").write_text("b\n", encoding="utf-8")

        # First port: both subdirs land in dst.
        porter.main([])
        dst_skill = dst / skill_name
        assert (dst_skill / "extra" / "asset.txt").is_file(), "seed port failed"
        assert (dst_skill / "kept" / "a.txt").is_file(), "seed port failed"

        # Now remove the nested source subdir entirely, and remove ONE file
        # from the still-populated subdir.
        shutil.rmtree(skill / "extra")
        (skill / "kept" / "b.txt").unlink()

        # drifted_skills() should flag the orphaned file/dir before re-port.
        porter_check = _load_porter(src, dst)
        drift_before = porter_check.drifted_skills()
        flags_orphan = any(
            "extra" in p.relative_to(dst).parts for p in drift_before
        )

        # Re-port.
        porter.main([])

        extra_dir = dst_skill / "extra"
        kept_dir = dst_skill / "kept"
        empty_orphan_lingers = extra_dir.exists()
        kept_intact = (kept_dir / "a.txt").is_file()
        kept_pruned_file_gone = not (kept_dir / "b.txt").exists()

        # After a clean re-port the drift guard must be quiet.
        porter_check2 = _load_porter(src, dst)
        drift_after = porter_check2.drifted_skills()

        # Direct guard test: an empty dst-only subdir with NO source counterpart
        # and NO orphan file must itself be flagged as drift (the blind spot the
        # fix closes — distinct from flagging the orphaned file).
        ghost = dst_skill / "ghost"
        ghost.mkdir(parents=True, exist_ok=True)
        porter_check3 = _load_porter(src, dst)
        drift_ghost = porter_check3.drifted_skills()
        guard_flags_empty_dir = any(
            "ghost" in p.relative_to(dst).parts for p in drift_ghost
        )
        ghost.rmdir()

        print(f"drifted_skills flags the orphan before re-port : {flags_orphan}")
        print(f"empty 'extra/' orphan dir lingers after re-port: {empty_orphan_lingers}")
        print(f"populated 'kept/' subdir left intact           : {kept_intact}")
        print(f"removed 'kept/b.txt' pruned                    : {kept_pruned_file_gone}")
        print(f"drift guard quiet after clean re-port          : {not drift_after}")
        print(f"drift guard flags a bare empty orphan dir      : {guard_flags_empty_dir}")

        ok = (
            flags_orphan
            and not empty_orphan_lingers
            and kept_intact
            and kept_pruned_file_gone
            and not drift_after
            and guard_flags_empty_dir
        )
        if ok:
            print("PASS: porter prunes empty orphan subdir and the guard catches it")
            return 0
        print("FAIL: porter leaves an empty orphan subdir / guard is blind to it")
        return 1


if __name__ == "__main__":
    sys.exit(main())
