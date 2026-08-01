import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';
import '../home_shell.dart';

class SideMenu extends StatelessWidget {
  final BridgeClient bridge;
  final String selectedId;
  final List<HackMateAction> actions;
  final bool sharingLogs;
  final ValueChanged<String> onSelect;
  final ValueChanged<bool> onSharingChanged;

  const SideMenu({
    super.key,
    required this.bridge,
    required this.selectedId,
    required this.actions,
    required this.sharingLogs,
    required this.onSelect,
    required this.onSharingChanged,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    final editConfigIndex = actions.indexWhere((a) => a.id == 'edit_config');
    final beforeSettings = actions.sublist(0, editConfigIndex + 1);
    final afterSettings = actions.sublist(editConfigIndex + 1);

    return Container(
      width: 300,
      color: scheme.surfaceContainerLow,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: scheme.primaryContainer,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(
                      Icons.terminal_rounded,
                      color: scheme.onPrimaryContainer,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Hackmate',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ),
                  _BridgeStatusDot(bridge: bridge),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                children: [
                  _MenuTile(
                    icon: Icons.home_rounded,
                    title: 'Welcome to Hackmate',
                    subtitle: 'Overview & getting started',
                    selected: selectedId == 'welcome',
                    onTap: () => onSelect('welcome'),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Divider(color: scheme.outlineVariant),
                  ),
                  for (final a in beforeSettings)
                    _MenuTile(
                      icon: a.icon,
                      title: a.title,
                      subtitle: a.subtitle,
                      selected: selectedId == a.id,
                      onTap: () => onSelect(a.id),
                    ),
                  _MenuTile(
                    icon: Icons.settings_rounded,
                    title: 'Settings',
                    subtitle: 'Theme and accent color',
                    selected: selectedId == 'settings',
                    onTap: () => onSelect('settings'),
                  ),
                  for (final a in afterSettings)
                    _MenuTile(
                      icon: a.icon,
                      title: a.title,
                      subtitle: a.subtitle,
                      selected: selectedId == a.id,
                      onTap: () => onSelect(a.id),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: _SharingLogsTile(
                value: sharingLogs,
                onChanged: onSharingChanged,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BridgeStatusDot extends StatelessWidget {
  final BridgeClient bridge;

  const _BridgeStatusDot({required this.bridge});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<BridgeStatus>(
      stream: bridge.statusStream,
      initialData: bridge.status,
      builder: (context, snapshot) {
        final status = snapshot.data ?? BridgeStatus.connecting;
        Color color;
        String tooltip;
        switch (status) {
          case BridgeStatus.connecting:
            color = Colors.amber;
            tooltip = 'Connecting to backend...';
          case BridgeStatus.connected:
            color = Colors.greenAccent;
            tooltip = 'Backend connected';
          case BridgeStatus.error:
            color = Colors.redAccent;
            tooltip = bridge.lastError ?? 'Backend error';
        }
        return Tooltip(
          message: tooltip,
          child: Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
        );
      },
    );
  }
}

class _MenuTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  const _MenuTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Material(
        color: selected ? scheme.secondaryContainer : Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 22,
                  color: selected
                      ? scheme.onSecondaryContainer
                      : scheme.onSurfaceVariant,
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              fontWeight: selected
                                  ? FontWeight.w700
                                  : FontWeight.w500,
                              color: selected
                                  ? scheme.onSecondaryContainer
                                  : scheme.onSurface,
                            ),
                      ),
                      const SizedBox(height: 1),
                      Text(
                        subtitle,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: selected
                                  ? scheme.onSecondaryContainer.withValues(
                                      alpha: 0.8,
                                    )
                                  : scheme.onSurfaceVariant,
                            ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SharingLogsTile extends StatelessWidget {
  final bool value;
  final ValueChanged<bool> onChanged;

  const _SharingLogsTile({required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [
          Icon(Icons.share_rounded, size: 20, color: scheme.onSurfaceVariant),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Sharing build logs',
              style: Theme.of(context).textTheme.labelLarge,
            ),
          ),
          Switch(value: value, onChanged: onChanged),
        ],
      ),
    );
  }
}
