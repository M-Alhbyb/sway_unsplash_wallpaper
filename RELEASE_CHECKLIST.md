# Release Checklist

## Pre-Release

### Code Quality
- [ ] All tests pass: `pytest`
- [ ] Code coverage >= 90%: `pytest --cov=unsplash_wallpaper`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Type checking passes: `mypy src/unsplash_wallpaper/`
- [ ] No outstanding critical bugs

### Documentation
- [ ] CHANGELOG.md updated with all changes
- [ ] README.md is current
- [ ] CONTRIBUTING.md is current
- [ ] API documentation is current
- [ ] Version bumped in `constants.py` and `pyproject.toml`

### Testing
- [ ] Unit tests pass on clean install
- [ ] Integration tests pass
- [ ] Stress tests pass (24h stability)
- [ ] Recovery tests pass
- [ ] Tested on target desktop environments (Sway, GNOME, KDE, Hyprland)

## Release Build

### Packaging
- [ ] `python -m build` succeeds
- [ ] `pip install .` works in clean virtualenv
- [ ] `pipx install .` works
- [ ] RPM build succeeds: `rpmbuild -ba data/unsplash-wallpaper.spec`
- [ ] Flatpak build succeeds: `flatpak-builder build data/com.unsplash.wallpaper.json`

### Verification
- [ ] `unsplash-wallpaper --version` shows correct version
- [ ] `unsplash-wallpaper --help` works
- [ ] `unsplash-wallpaper --diagnostics` runs without errors
- [ ] Desktop launcher appears in application menu
- [ ] Tray icon appears in system tray
- [ ] First-run wizard displays correctly
- [ ] Wallpaper downloads and applies
- [ ] Scheduler changes wallpaper at configured interval
- [ ] Notifications appear
- [ ] History shows all downloaded wallpapers

### System Integration
- [ ] `unsplash-wallpaper --install-service` installs systemd service
- [ ] `unsplash-wallpaper --remove-service` removes systemd service
- [ ] Autostart enables and disables correctly
- [ ] Daemon mode runs without UI
- [ ] Tray mode runs with icon

## Release

### GitHub
- [ ] Tag created: `git tag v<VERSION>`
- [ ] Tag pushed: `git push --tags`
- [ ] GitHub release created
- [ ] Release notes written
- [ ] Binary/source archives attached

### Post-Release
- [ ] Verify pip install from PyPI
- [ ] Verify COPR/RPM update
- [ ] Update Flatpak on Flathub
- [ ] Announce release on relevant channels

## Emergency Rollback

### If release has critical issues:

1. `git revert <release-commit>`
2. `git push`
3. Create new patch release with fix
4. Remove problematic release from PyPI/COPR
5. Notify users of rollback and fix
