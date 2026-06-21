<?php
header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

echo "HOST=" . ($_SERVER['HTTP_HOST'] ?? '') . "\n";
echo "URI=" . ($_SERVER['REQUEST_URI'] ?? '') . "\n";

echo "COOKIES:\n";
foreach ($_COOKIE as $k => $v) {
    echo $k . "=" . $v . "\n";
}

echo "\nTrying to set test cookie...\n";
$ok = setcookie('OM_TEST', '1', time()+3600, '/', '', false, true);
echo "setcookie_return=" . ($ok ? "true" : "false") . "\n";

echo "NOTE: reload this page after first open and check OM_TEST appears above.\n";