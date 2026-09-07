import 'package:flutter_test/flutter_test.dart';
import 'package:labelsure_flutter/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('LabelSureApp smoke test', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const LabelSureApp());
    expect(find.byType(LabelSureApp), findsOneWidget);
  });
}
