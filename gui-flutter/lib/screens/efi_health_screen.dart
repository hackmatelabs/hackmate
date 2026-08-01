import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';

class EfiHealthScreen extends StatefulWidget {
  final BridgeClient bridge;

  const EfiHealthScreen({super.key, required this.bridge});

  @override
  State<EfiHealthScreen> createState() => _EfiHealthScreenState();
}

class _EfiHealthScreenState extends State<EfiHealthScreen> {
  final _pathController = TextEditingController();
  Future<Map<String, dynamic>>? _future;

  void _audit() {
    final path = _pathController.text.trim();
    if (path.isEmpty) return;
    setState(() {
      _future = widget.bridge
          .call('efi_health.audit', {'efi_root': path}).then((r) => r as Map<String, dynamic>);
    });
  }

  @override
  void dispose() {
    _pathController.dispose();
    super.dispose();
  }

  Color _levelColor(ColorScheme scheme, String level) {
    switch (level) {
      case 'critical':
        return scheme.error;
      case 'warn':
        return Colors.amber;
      case 'ok':
        return Colors.greenAccent;
      default:
        return scheme.onSurfaceVariant;
    }
  }

  IconData _levelIcon(String level) {
    switch (level) {
      case 'critical':
        return Icons.error_rounded;
      case 'warn':
        return Icons.warning_amber_rounded;
      case 'ok':
        return Icons.check_circle_rounded;
      default:
        return Icons.info_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: scheme.secondaryContainer,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Icon(Icons.health_and_safety_rounded, size: 28, color: scheme.onSecondaryContainer),
              ),
              const SizedBox(width: 16),
              Text(
                'EFI Health Check',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _pathController,
                  decoration: const InputDecoration(
                    labelText: 'EFI folder path',
                    hintText: r'D:\EFI (the folder containing OC\)',
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (_) => _audit(),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.icon(
                onPressed: _audit,
                icon: const Icon(Icons.fact_check_rounded),
                label: const Text('Scan'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Expanded(
            child: _future == null
                ? Center(
                    child: Text(
                      'Enter your EFI folder path to run a health check.',
                      style: TextStyle(color: scheme.onSurfaceVariant),
                    ),
                  )
                : FutureBuilder<Map<String, dynamic>>(
                    future: _future,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState != ConnectionState.done) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (snapshot.hasError) {
                        return Center(
                          child: Text(
                            snapshot.error is BridgeException
                                ? (snapshot.error as BridgeException).message
                                : snapshot.error.toString(),
                            style: TextStyle(color: scheme.error),
                          ),
                        );
                      }
                      final data = snapshot.data!;
                      final findings = data['findings'] as List<dynamic>;
                      final summary = (data['summary'] as Map<String, dynamic>);

                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: 12,
                            children: [
                              for (final level in ['critical', 'warn', 'info', 'ok'])
                                Chip(
                                  avatar: Icon(_levelIcon(level), size: 18, color: _levelColor(scheme, level)),
                                  label: Text('${summary[level] ?? 0} $level'),
                                ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Expanded(
                            child: findings.isEmpty
                                ? const Center(child: Text('No findings.'))
                                : ListView.separated(
                                    itemCount: findings.length,
                                    separatorBuilder: (_, _) => const SizedBox(height: 8),
                                    itemBuilder: (context, index) {
                                      final f = findings[index] as Map<String, dynamic>;
                                      final level = f['level'] as String? ?? 'info';
                                      return Card(
                                        child: ListTile(
                                          leading: Icon(_levelIcon(level), color: _levelColor(scheme, level)),
                                          title: Text(f['title'] as String? ?? ''),
                                          subtitle: Text(f['detail'] as String? ?? ''),
                                        ),
                                      );
                                    },
                                  ),
                          ),
                        ],
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
