# Copyright (C) 2024 Microsoft Corporation
#
# Author: Dan Streetman <ddstreet@microsoft.com>
#
# This file is part of cloud-init. See LICENSE file for license information.

import logging

from cloudinit import subp, util
from cloudinit.distros import rhel
from cloudinit.net.netplan import CLOUDINIT_NETPLAN_FILE

LOG = logging.getLogger(__name__)

NETWORK_FILE_HEADER = """\
# This file is generated from information provided by the datasource.  Changes
# to it will not persist across an instance reboot. To disable cloud-init's
# network configuration capabilities, write a file
# /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg with the following:
# network: {config: disabled}
"""


class Distro(rhel.Distro):
    def __init__(self, name, cfg, paths):
        super().__init__(self, name, cfg, paths)
        self.osfamily = "azurelinux"

        self.network_conf_dir = "/etc/systemd/network/"
        self.systemd_locale_conf_fn = "/etc/locale.conf"
        self.resolve_conf_fn = "/etc/systemd/resolved.conf"
        self.init_cmd = ["systemctl"]

        self.network_conf_fn = {"netplan": CLOUDINIT_NETPLAN_FILE}
        self.renderer_configs = {
            "networkd": {
                "resolv_conf_fn": self.resolve_conf_fn,
                "network_conf_dir": self.network_conf_dir,
            },
            "netplan": {
                "netplan_path": self.network_conf_fn["netplan"],
                "netplan_header": NETWORK_FILE_HEADER,
                "postcmds": "True",
            },
        }

    def package_command(self, command, args=None, pkgs=None):
        if pkgs is None:
            pkgs = []

        if subp.which("dnf"):
            LOG.debug("Using DNF for package management")
            cmd = ["dnf"]
        if subp.which("tdnf"):
            LOG.debug("Using TDNF for package management")
            cmd = ["tdnf"]
        else:
            LOG.debug("Using YUM for package management")
            # the '-t' argument makes yum tolerant of errors on the command
            # line with regard to packages.
            #
            # For example: if you request to install foo, bar and baz and baz
            # is installed; yum won't error out complaining that baz is already
            # installed.
            cmd = ["yum", "-t"]
        # Determines whether or not yum prompts for confirmation
        # of critical actions. We don't want to prompt...
        cmd.append("-y")

        if args and isinstance(args, str):
            cmd.append(args)
        elif args and isinstance(args, list):
            cmd.extend(args)

        cmd.append(command)

        pkglist = util.expand_package_list("%s-%s", pkgs)
        cmd.extend(pkglist)

        # Allow the output of this to flow outwards (ie not be captured)
        subp.subp(cmd, capture=False)
