import 'package:flutter/material.dart';

import '../bridge/bridge_client.dart';

typedef AsyncScreenBuilder<T> = Widget Function(BuildContext context, T data);

class AsyncScreen<T> extends StatefulWidget {
  final BridgeClient bridge;
  final String title;
  final IconData icon;
  final Future<T> Function(BridgeClient bridge) load;
  final AsyncScreenBuilder<T> builder;
  final Widget? headerTrailing;

  const AsyncScreen({
    super.key,
    required this.bridge,
    required this.title,
    required this.icon,
    required this.load,
    required this.builder,
    this.headerTrailing,
  });

  @override
  State<AsyncScreen<T>> createState() => AsyncScreenState<T>();
}

class AsyncScreenState<T> extends State<AsyncScreen<T>> {
  late Future<T> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.load(widget.bridge);
  }

  void reload() {
    setState(() => _future = widget.load(widget.bridge));
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
                child: Icon(widget.icon, size: 28, color: scheme.onSecondaryContainer),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  widget.title,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              if (widget.headerTrailing != null) widget.headerTrailing!,
              IconButton(
                icon: const Icon(Icons.refresh_rounded),
                tooltip: 'Refresh',
                onPressed: reload,
              ),
            ],
          ),
          const SizedBox(height: 24),
          Expanded(
            child: FutureBuilder<T>(
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
                return widget.builder(context, snapshot.data as T);
              },
            ),
          ),
        ],
      ),
    );
  }
}
