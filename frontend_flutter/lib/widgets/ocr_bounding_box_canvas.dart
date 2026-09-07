import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../core/api_client.dart';

class OCRBlockData {
  final String id;
  final String rawText;
  final String normalizedText;
  final double confidence;
  final String confidenceTier;
  final int readingOrder;
  final int lineNumber;
  final List<Offset> polygon;
  final Rect boundingBox;

  OCRBlockData({
    required this.id,
    required this.rawText,
    required this.normalizedText,
    required this.confidence,
    required this.confidenceTier,
    required this.readingOrder,
    required this.lineNumber,
    required this.polygon,
    required this.boundingBox,
  });

  factory OCRBlockData.fromJson(Map<String, dynamic> json, int defaultIndex) {
    final rawPoly = json['polygon'];
    final List<Offset> polyPoints = [];
    if (rawPoly is List) {
      for (final pt in rawPoly) {
        if (pt is List && pt.length >= 2) {
          polyPoints.add(Offset(
            (pt[0] as num).toDouble(),
            (pt[1] as num).toDouble(),
          ));
        }
      }
    }

    final bboxMap = json['bounding_box'] as Map<String, dynamic>?;
    final Rect bbox = bboxMap != null
        ? Rect.fromLTWH(
            (bboxMap['x'] as num? ?? 0).toDouble(),
            (bboxMap['y'] as num? ?? 0).toDouble(),
            (bboxMap['width'] as num? ?? 0).toDouble(),
            (bboxMap['height'] as num? ?? 0).toDouble(),
          )
        : (polyPoints.isNotEmpty
            ? Rect.fromPoints(polyPoints.first, polyPoints.last)
            : Rect.zero);

    final conf = (json['confidence'] as num? ?? 0).toDouble();
    String tier = json['confidence_tier']?.toString() ?? '';
    if (tier.isEmpty) {
      tier = conf >= 0.85 ? 'GOOD' : conf >= 0.60 ? 'REVIEW' : 'LOW';
    }

    return OCRBlockData(
      id: json['id']?.toString() ?? json['ocr_block_id']?.toString() ?? 'blk_$defaultIndex',
      rawText: json['raw_text']?.toString() ?? '',
      normalizedText: json['normalized_text']?.toString() ?? json['raw_text']?.toString() ?? '',
      confidence: conf,
      confidenceTier: tier,
      readingOrder: json['reading_order'] as int? ?? json['sequence_order'] as int? ?? defaultIndex,
      lineNumber: json['line_number'] as int? ?? defaultIndex,
      polygon: polyPoints,
      boundingBox: bbox,
    );
  }
}

class OCRBoundingBoxCanvas extends StatefulWidget {
  final String imageUrl;
  final String? altText;
  final List<OCRBlockData> blocks;
  final String? selectedBlockId;
  final String? hoveredBlockId;
  final ValueChanged<OCRBlockData>? onSelectBlock;
  final ValueChanged<String?>? onHoverBlock;
  final bool showOverlays;
  final bool showLabels;

  const OCRBoundingBoxCanvas({
    super.key,
    required this.imageUrl,
    this.altText,
    required this.blocks,
    this.selectedBlockId,
    this.hoveredBlockId,
    this.onSelectBlock,
    this.onHoverBlock,
    this.showOverlays = true,
    this.showLabels = true,
  });

  @override
  State<OCRBoundingBoxCanvas> createState() => _OCRBoundingBoxCanvasState();
}

class _OCRBoundingBoxCanvasState extends State<OCRBoundingBoxCanvas> {
  ui.Image? _decodedImage;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadImage();
  }

  @override
  void didUpdateWidget(OCRBoundingBoxCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.imageUrl != widget.imageUrl) {
      _loadImage();
    }
  }

  Future<void> _loadImage() async {
    setState(() => _loading = true);
    try {
      final bytes = await ApiClient().getBytes(widget.imageUrl);
      final codec = await ui.instantiateImageCodec(bytes);
      final frame = await codec.getNextFrame();
      if (mounted) {
        setState(() {
          _decodedImage = frame.image;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _handleTapDown(TapDownDetails details, BoxConstraints constraints) {
    if (_decodedImage == null || widget.blocks.isEmpty) return;

    final imgW = _decodedImage!.width.toDouble();
    final imgH = _decodedImage!.height.toDouble();

    // Fitted box calculation
    final fittedSizes = applyBoxFit(BoxFit.contain, Size(imgW, imgH), Size(constraints.maxWidth, constraints.maxHeight));
    final dx = (constraints.maxWidth - fittedSizes.destination.width) / 2;
    final dy = (constraints.maxHeight - fittedSizes.destination.height) / 2;

    final localPos = details.localPosition;
    if (localPos.dx < dx || localPos.dx > dx + fittedSizes.destination.width ||
        localPos.dy < dy || localPos.dy > dy + fittedSizes.destination.height) {
      return;
    }

    final scaleX = imgW / fittedSizes.destination.width;
    final scaleY = imgH / fittedSizes.destination.height;
    final imageX = (localPos.dx - dx) * scaleX;
    final imageY = (localPos.dy - dy) * scaleY;
    final clickedPoint = Offset(imageX, imageY);

    for (final block in widget.blocks) {
      if (block.polygon.isNotEmpty) {
        final path = Path()..addPolygon(block.polygon, true);
        if (path.contains(clickedPoint)) {
          widget.onSelectBlock?.call(block);
          return;
        }
      } else if (block.boundingBox.contains(clickedPoint)) {
        widget.onSelectBlock?.call(block);
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const SizedBox(
        height: 380,
        child: Center(
          child: CircularProgressIndicator(color: Color(0xFF10B981), strokeWidth: 2),
        ),
      );
    }

    if (_decodedImage == null) {
      return Container(
        height: 380,
        color: const Color(0xFF0F172A),
        child: const Center(
          child: Text('Unable to display evidence image', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        return GestureDetector(
          onTapDown: (details) => _handleTapDown(details, constraints),
          child: SizedBox(
            width: constraints.maxWidth,
            height: constraints.maxHeight > 0 && constraints.maxHeight.isFinite ? constraints.maxHeight : 450,
            child: CustomPaint(
              painter: _OCRBoxesPainter(
                image: _decodedImage!,
                blocks: widget.blocks,
                selectedBlockId: widget.selectedBlockId,
                hoveredBlockId: widget.hoveredBlockId,
                showOverlays: widget.showOverlays,
                showLabels: widget.showLabels,
              ),
            ),
          ),
        );
      },
    );
  }
}

class _OCRBoxesPainter extends CustomPainter {
  final ui.Image image;
  final List<OCRBlockData> blocks;
  final String? selectedBlockId;
  final String? hoveredBlockId;
  final bool showOverlays;
  final bool showLabels;

  _OCRBoxesPainter({
    required this.image,
    required this.blocks,
    required this.selectedBlockId,
    required this.hoveredBlockId,
    required this.showOverlays,
    required this.showLabels,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final imgW = image.width.toDouble();
    final imgH = image.height.toDouble();

    final fittedSizes = applyBoxFit(BoxFit.contain, Size(imgW, imgH), size);
    final dx = (size.width - fittedSizes.destination.width) / 2;
    final dy = (size.height - fittedSizes.destination.height) / 2;
    final destRect = Rect.fromLTWH(dx, dy, fittedSizes.destination.width, fittedSizes.destination.height);

    // 1. Draw base image
    final srcRect = Rect.fromLTWH(0, 0, imgW, imgH);
    canvas.drawImageRect(image, srcRect, destRect, Paint());

    if (!showOverlays) return;

    // Scale coordinates from image to canvas
    final scaleX = fittedSizes.destination.width / imgW;
    final scaleY = fittedSizes.destination.height / imgH;

    for (final block in blocks) {
      final isSelected = selectedBlockId == block.id;
      final isHovered = hoveredBlockId == block.id;
      final isActive = isSelected || isHovered;

      Color strokeColor;
      Color fillColor;
      Color badgeBg;

      switch (block.confidenceTier) {
        case 'GOOD':
          strokeColor = isActive ? const Color(0xFF047857) : const Color(0xFF059669);
          fillColor = isActive ? const Color(0x6610B981) : const Color(0x2E10B981);
          badgeBg = const Color(0xFF065F46);
          break;
        case 'LOW':
          strokeColor = isActive ? const Color(0xFFBE123C) : const Color(0xFFE11D48);
          fillColor = isActive ? const Color(0x80E11D48) : const Color(0x40E11D48);
          badgeBg = const Color(0xFF9F1239);
          break;
        case 'REVIEW':
        default:
          strokeColor = isActive ? const Color(0xFFB45309) : const Color(0xFFD97706);
          fillColor = isActive ? const Color(0x73F59E0B) : const Color(0x38F59E0B);
          badgeBg = const Color(0xFF92400E);
          break;
      }

      final fillPaint = Paint()
        ..color = fillColor
        ..style = PaintingStyle.fill;

      final strokePaint = Paint()
        ..color = strokeColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = isActive ? 2.5 : 1.5;

      Path path;
      Offset firstPt;

      if (block.polygon.length >= 3) {
        path = Path();
        firstPt = Offset(
          dx + block.polygon.first.dx * scaleX,
          dy + block.polygon.first.dy * scaleY,
        );
        path.moveTo(firstPt.dx, firstPt.dy);
        for (int i = 1; i < block.polygon.length; i++) {
          path.lineTo(
            dx + block.polygon[i].dx * scaleX,
            dy + block.polygon[i].dy * scaleY,
          );
        }
        path.close();
      } else {
        final scaledRect = Rect.fromLTWH(
          dx + block.boundingBox.left * scaleX,
          dy + block.boundingBox.top * scaleY,
          block.boundingBox.width * scaleX,
          block.boundingBox.height * scaleY,
        );
        path = Path()..addRect(scaledRect);
        firstPt = Offset(scaledRect.left, scaledRect.top);
      }

      canvas.drawPath(path, fillPaint);
      canvas.drawPath(path, strokePaint);

      // 2. Reading order numbered badges
      if (showLabels) {
        final labelText = '${block.readingOrder + 1}';
        final textSpan = TextSpan(
          text: labelText,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 9,
            fontWeight: FontWeight.bold,
            fontFamily: 'monospace',
          ),
        );
        final textPainter = TextPainter(
          text: textSpan,
          textDirection: TextDirection.ltr,
        )..layout();

        final badgeRect = RRect.fromRectAndRadius(
          Rect.fromLTWH(
            firstPt.dx,
            firstPt.dy - textPainter.height - 4,
            textPainter.width + 8,
            textPainter.height + 4,
          ),
          const Radius.circular(3),
        );

        canvas.drawRRect(badgeRect, Paint()..color = badgeBg);
        textPainter.paint(canvas, Offset(firstPt.dx + 4, firstPt.dy - textPainter.height - 2));
      }
    }
  }

  @override
  bool shouldRepaint(covariant _OCRBoxesPainter oldDelegate) {
    return oldDelegate.selectedBlockId != selectedBlockId ||
        oldDelegate.hoveredBlockId != hoveredBlockId ||
        oldDelegate.showOverlays != showOverlays ||
        oldDelegate.showLabels != showLabels ||
        oldDelegate.blocks != blocks;
  }
}
