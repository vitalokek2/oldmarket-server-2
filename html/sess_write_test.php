<?php
require_once 'session_bootstrap.php';
$_SESSION['ping'] = time();
session_write_close();
header("Location: cookie_check.php");
exit;