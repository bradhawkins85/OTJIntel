from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_env_example_sets_auto_refresh_false() -> None:
    env_template = PROJECT_ROOT / ".env.example"
    contents = env_template.read_text(encoding="utf-8")
    assert "ENABLE_AUTO_REFRESH=false" in contents


def test_env_example_does_not_expose_feature_pack_toggle() -> None:
    env_template = PROJECT_ROOT / ".env.example"
    contents = env_template.read_text(encoding="utf-8")
    assert "FEATURE_PACKS=" not in contents


def test_restart_script_seeds_auto_refresh() -> None:
    script_path = PROJECT_ROOT / "scripts" / "restart.sh"
    contents = script_path.read_text(encoding="utf-8")
    assert 'ensure_env_default "$PYTHON_BIN" "ENABLE_AUTO_REFRESH" "false"' in contents


def test_upgrade_script_seeds_auto_refresh() -> None:
    script_path = PROJECT_ROOT / "scripts" / "upgrade.sh"
    contents = script_path.read_text(encoding="utf-8")
    assert 'ensure_env_default "$PYTHON_INTERPRETER" "ENABLE_AUTO_REFRESH" "false"' in contents


def test_install_environment_seeds_auto_refresh() -> None:
    script_path = PROJECT_ROOT / "scripts" / "install_environment.sh"
    contents = script_path.read_text(encoding="utf-8")
    assert 'ensure_env_default "ENABLE_AUTO_REFRESH" "false"' in contents


def test_install_environment_aligns_env_file_with_selected_environment() -> None:
    script_path = PROJECT_ROOT / "scripts" / "install_environment.sh"
    contents = script_path.read_text(encoding="utf-8")
    assert 'set_env_value "ENVIRONMENT" "$ENVIRONMENT"' in contents


def test_install_environment_installs_and_starts_systemd_service() -> None:
    script_path = PROJECT_ROOT / "scripts" / "install_environment.sh"
    contents = script_path.read_text(encoding="utf-8")
    assert "install_systemd_service()" in contents
    assert 'run_privileged systemctl daemon-reload' in contents
    assert 'run_privileged systemctl enable --now "$unit_name"' in contents


def test_install_environment_uses_distinct_development_service_name() -> None:
    script_path = PROJECT_ROOT / "scripts" / "install_environment.sh"
    contents = script_path.read_text(encoding="utf-8")
    assert 'printf \'%s\' "myportal-development"' in contents
