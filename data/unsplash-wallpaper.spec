%global __python3 /usr/bin/python3

Name:           unsplash-wallpaper
Version:        1.0.0
Release:        1%{?dist}
Summary:        Automatic Unsplash wallpaper changer for Linux desktop

License:        MIT
URL:            https://github.com/unsplash-wallpaper
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-requests
BuildRequires:  python3-gobject-base

Requires:       python3
Requires:       python3-requests
Requires:       python3-gobject-base
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       swaybg
Requires:       libnotify
Requires:       xdg-utils

%description
Unsplash Wallpaper Manager automatically downloads wallpapers from Unsplash
and applies them to your desktop environment. Supports Sway (Wayland) with
planned support for Hyprland, GNOME, and KDE.

Features:
  - Automatic wallpaper download from Unsplash
  - Scheduled wallpaper changes
  - Category-based wallpaper selection
  - Wallpaper history management
  - System tray integration
  - GTK4 + Libadwaita user interface

%prep
%autosetup

%build
%py3_build

%install
%py3_install

install -D -m 0644 data/com.unsplash.wallpaper.desktop \
  %{buildroot}%{_datadir}/applications/com.unsplash.wallpaper.desktop

install -D -m 0644 data/com.unsplash.wallpaper.service \
  %{buildroot}%{_userunitdir}/com.unsplash.wallpaper.service

install -D -m 0644 data/com.unsplash.wallpaper.timer \
  %{buildroot}%{_userunitdir}/com.unsplash.wallpaper.timer

%files
%{python3_sitelib}/unsplash_wallpaper*
%{_bindir}/unsplash-wallpaper
%{_datadir}/applications/com.unsplash.wallpaper.desktop
%{_userunitdir}/com.unsplash.wallpaper.service
%{_userunitdir}/com.unsplash.wallpaper.timer

%changelog
* Mon Jun 01 2026 Unsplash Wallpaper Team <dev@unsplash-wallpaper.local> - 1.0.0-1
- Initial release
