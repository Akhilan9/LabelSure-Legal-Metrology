import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/api_client.dart';
import 'core/auth_state.dart';
import 'core/router.dart';
import 'core/theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiClient().init();
  runApp(const LabelSureApp());
}

class LabelSureApp extends StatefulWidget {
  const LabelSureApp({super.key});

  @override
  State<LabelSureApp> createState() => _LabelSureAppState();
}

class _LabelSureAppState extends State<LabelSureApp> {
  late final AuthProvider _authProvider;

  @override
  void initState() {
    super.initState();
    _authProvider = AuthProvider();
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: _authProvider,
      child: Builder(
        builder: (context) {
          final auth = context.watch<AuthProvider>();
          final router = createRouter(auth);

          return MaterialApp.router(
            title: 'LabelSure · Legal Metrology Intelligence',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.darkTheme,
            routerConfig: router,
          );
        },
      ),
    );
  }
}
