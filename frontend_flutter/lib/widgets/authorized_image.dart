import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../core/api_client.dart';

class AuthorizedImage extends StatefulWidget {
  final String? src;
  final String? alt;
  final double? width;
  final double? height;
  final BoxFit fit;
  final VoidCallback? onTap;
  final void Function(int width, int height)? onLoadDimensions;

  const AuthorizedImage({
    super.key,
    required this.src,
    this.alt,
    this.width,
    this.height,
    this.fit = BoxFit.contain,
    this.onTap,
    this.onLoadDimensions,
  });

  static final Map<String, Uint8List> _cache = {};

  @override
  State<AuthorizedImage> createState() => _AuthorizedImageState();
}

class _AuthorizedImageState extends State<AuthorizedImage> {
  Uint8List? _bytes;
  bool _loading = true;
  bool _error = false;

  @override
  void initState() {
    super.initState();
    _loadImage();
  }

  @override
  void didUpdateWidget(AuthorizedImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.src != widget.src) {
      _loadImage();
    }
  }

  Future<void> _loadImage() async {
    final src = widget.src;
    if (src == null || src.isEmpty) {
      if (mounted) setState(() => _loading = false);
      return;
    }

    if (AuthorizedImage._cache.containsKey(src)) {
      if (mounted) {
        setState(() {
          _bytes = AuthorizedImage._cache[src];
          _loading = false;
          _error = false;
        });
      }
      return;
    }

    if (mounted) {
      setState(() {
        _loading = true;
        _error = false;
      });
    }

    try {
      final bytes = await ApiClient().getBytes(src);
      AuthorizedImage._cache[src] = bytes;

      if (mounted) {
        setState(() {
          _bytes = bytes;
          _loading = false;
          _error = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _error = true;
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    Widget content;

    if (_loading) {
      content = Container(
        width: widget.width,
        height: widget.height,
        color: const Color(0xFF0F172A),
        child: const Center(
          child: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10B981)),
          ),
        ),
      );
    } else if (_error || _bytes == null) {
      content = Container(
        width: widget.width,
        height: widget.height,
        color: const Color(0xFF1E293B),
        padding: const EdgeInsets.all(8),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.broken_image_outlined, size: 28, color: Color(0xFF64748B)),
            const SizedBox(height: 4),
            Text(
              widget.alt ?? 'No Preview',
              style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      );
    } else {
      content = Image.memory(
        _bytes!,
        width: widget.width,
        height: widget.height,
        fit: widget.fit,
        frameBuilder: (context, child, frame, wasSynchronouslyLoaded) {
          return child;
        },
      );
    }

    if (widget.onTap != null) {
      return GestureDetector(
        onTap: widget.onTap,
        child: content,
      );
    }

    return content;
  }
}
