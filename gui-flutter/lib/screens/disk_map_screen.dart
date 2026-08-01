import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';
import '../widgets/async_screen.dart';

class DiskMapScreen extends StatelessWidget {
  final BridgeClient bridge;

  const DiskMapScreen({super.key, required this.bridge});

  @override
  Widget build(BuildContext context) {
    return AsyncScreen<Map<String, dynamic>>(
      bridge: bridge,
      title: 'Dual Boot / Disk Map',
      icon: Icons.dns_rounded,
      load: (b) async => await b.call('dualboot.scan_disks') as Map<String, dynamic>,
      builder: (context, data) {
        final scheme = Theme.of(context).colorScheme;
        final disks = data['disks'] as List<dynamic>;
        final bootloaders = data['bootloaders'] as Map<String, dynamic>;

        if (disks.isEmpty) {
          return const Center(child: Text('No disks detected.'));
        }

        return ListView.separated(
          itemCount: disks.length,
          separatorBuilder: (_, _) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final disk = disks[index] as Map<String, dynamic>;
            final partitions = disk['partitions'] as List<dynamic>;

            return Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.storage_rounded, color: scheme.primary),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            '${disk['device']} — ${disk['model']}',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                          ),
                        ),
                        Text(
                          '${disk['size']} · ${disk['transport']} · ${disk['is_gpt'] == true ? 'GPT' : 'MBR'}',
                          style: TextStyle(color: scheme.onSurfaceVariant),
                        ),
                      ],
                    ),
                    const Divider(height: 24),
                    for (final p in partitions)
                      _PartitionRow(
                        partition: p as Map<String, dynamic>,
                        bootloader: bootloaders[p['device']] as Map<String, dynamic>?,
                      ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}

class _PartitionRow extends StatelessWidget {
  final Map<String, dynamic> partition;
  final Map<String, dynamic>? bootloader;

  const _PartitionRow({required this.partition, this.bootloader});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isEfi = partition['is_efi'] == true;
    final label = (partition['label'] as String?)?.isNotEmpty == true
        ? partition['label']
        : (partition['fs_type'] as String?)?.isNotEmpty == true
            ? partition['fs_type']
            : 'Unlabeled';

    final tags = <String>[];
    if (bootloader != null) {
      if (bootloader!['windows'] == true) tags.add('Windows');
      if (bootloader!['opencore'] == true) tags.add('OpenCore');
      if (bootloader!['linux_grub'] == true) tags.add('GRUB');
      if (bootloader!['linux_efi'] == true) tags.add('Linux EFI');
      if (bootloader!['refind'] == true) tags.add('rEFInd');
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(
            isEfi ? Icons.bolt_rounded : Icons.crop_square_rounded,
            size: 18,
            color: isEfi ? scheme.tertiary : scheme.onSurfaceVariant,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text('${partition['device']} — $label'),
          ),
          if (partition['mount'] != null && (partition['mount'] as String).isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Text(partition['mount'], style: TextStyle(color: scheme.onSurfaceVariant)),
            ),
          Text(partition['size'] as String? ?? '', style: TextStyle(color: scheme.onSurfaceVariant)),
          const SizedBox(width: 12),
          if (tags.isNotEmpty)
            Wrap(
              spacing: 6,
              children: [for (final t in tags) Chip(label: Text(t), visualDensity: VisualDensity.compact)],
            ),
        ],
      ),
    );
  }
}
