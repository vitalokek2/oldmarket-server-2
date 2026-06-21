<?php
require_once 'session_bootstrap.php';
header('Content-Type: text/plain; charset=utf-8');

echo "HOST=" . ($_SERVER['HTTP_HOST'] ?? '') . "\n";
echo "SESSION_NAME=" . session_name() . "\n";
echo "SESSION_ID=" . session_id() . "\n";
echo "COOKIE=" . (isset($_COOKIE[session_name()]) ? $_COOKIE[session_name()] : 'NO_COOKIE') . "\n";
echo "SESSION=";
var_export($_SESSION);