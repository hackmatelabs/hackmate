import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';
import '../widgets/async_screen.dart';

class BuildHistoryScreen extends StatelessWidget {
  final BridgeClient bridge;

  const BuildHistoryScreen({super.key, required this.bridge});

  @override
  Widget build(BuildContext context) {
    return AsyncScreen<List<dynamic>>(
      bridge: bridge,
      title: 'Build History',
      icon: Icons.history_rounded,
      load: (b) async => await b.call('build_history.list') as List<dynamic>,
      builder: (context, builds) {
        if (builds.isEmpty) {
          return const Center(child: Text('No builds recorded yet.'));
        }
        return ListView.separated(
          itemCount: builds.length,
          separatorBuilder: (_, _) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final build = builds[index] as Map<String, dynamic>;
            final ts = build['timestamp'] as num? ?? 0;
            final date = DateTime.fromMillisecondsSinceEpoch(ts.toInt() * 1000);
            final macos = build['macos_version'] as String? ?? 'Unknown macOS';
            final efiPath = build['efi_output_path'] as String? ?? '';

            return Card(
              child: ListTile(
                leading: const Icon(Icons.construction_rounded),
                title: Text(macos),
                subtitle: Text(
                  '${date.toLocal()}${efiPath.isNotEmpty ? '\n$efiPath' : ''}',
                ),
                isThreeLine: efiPath.isNotEmpty,
                trailing: IconButton(
                  icon: const Icon(Icons.delete_outline_rounded),
                  onPressed: () async {
                    final state = context.findAncestorStateOfType<AsyncScreenState<List<dynamic>>>();
                    await bridge.call('build_history.delete', {'entry_id': build['id']});
                    state?.reload();
                  },
                ),
              ),
            );
          },
        );
      },
    );
  }
}
