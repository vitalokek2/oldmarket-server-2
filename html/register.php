<?php
require_once __DIR__ . '/auth_cookie.php';

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$bad_words = [];

$error = null;
$success = null;
$stage = 'form';
$link_code = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? 'start';

    if ($action === 'start') {
        $username = trim($_POST['username'] ?? '');
        $email    = trim($_POST['email'] ?? '');
        $password = trim($_POST['password'] ?? '');

        $errors = [];

        if (strlen($username) < 3 || strlen($username) > 15) {
            $errors[] = "Логин должен быть от 3 до 15 символов";
        }
        if (!preg_match('/^[a-zA-Z0-9]+$/', $username)) {
            $errors[] = "Логин может содержать только латинские буквы и цифры";
        }

        $uname_lower = strtolower($username);
        foreach ($bad_words as $bw) {
            if (strpos($uname_lower, $bw) !== false) {
                $errors[] = "Логин содержит запрещённые слова";
                break;
            }
        }

        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $errors[] = "Некорректный email";
        }

        if (strlen($password) < 4) {
            $errors[] = "Пароль должен быть от 4 символов";
        }

        if (!empty($errors)) {
            $error = implode("<br>", $errors);
            $stage = 'form';
        } else {
            $res = api_post_json('/api/register/start', [
                "username" => $username,
                "email"    => $email,
                "password" => $password
            ]);

            if ($res === false) {
                $error = "Ошибка соединения с сервером";
                $stage = 'form';
            } else {
                $j = json_decode($res, true);
                if (is_array($j) && !empty($j["success"]) && !empty($j["code"])) {
                    $link_code = $j["code"];
                    $stage = 'link';
                } else {
                    $error = $j["error"] ?? "Ошибка регистрации";
                    $stage = 'form';
                }
            }
        }
    }

    if ($action === 'check') {
        $link_code = trim($_POST['code'] ?? '');

        $statusRes = api_post_json('/api/register/status', [
            "code" => $link_code
        ]);

        if ($statusRes === false) {
            $error = "Ошибка соединения с сервером";
            $stage = 'link';
        } else {
            $sj = json_decode($statusRes, true);
            if (!is_array($sj) || !empty($sj["error"])) {
                $error = $sj["error"] ?? "Ошибка проверки привязки";
                $stage = 'link';
            } else {
                if (empty($sj["is_linked"])) {
                    $error = "Telegram ещё не привязан. Отправьте код в бота и попробуйте снова.";
                    $stage = 'link';
                } else {
                    $finishRes = api_post_json('/api/register/finish', [
                        "code" => $link_code
                    ]);

                    if ($finishRes === false) {
                        $error = "Привязка найдена, но завершить регистрацию не удалось.";
                        $stage = 'link';
                    } else {
                        $fj = json_decode($finishRes, true);
                        if (is_array($fj) && !empty($fj["success"])) {
                            $uid   = (int)$fj["user_id"];
                            $uname = (string)$fj["username"];

                            $avatar = "default_avatar.png";
                            $is_premium = 0;

                            $profile_json = api_get('/api/user/' . $uid . '/profile');
                            if ($profile_json !== false) {
                                $p = json_decode($profile_json, true);
                                if (is_array($p) && empty($p["error"])) {
                                    $avatar = $p["avatar"] ?? $avatar;
                                    $is_premium = (int)($p["is_premium"] ?? 0);
                                }
                            }

                            auth_set_cookies($uid, $uname, $avatar, $is_premium);
                            header("Location: /index.php");
                            exit;
                        } else {
                            $error = $fj["error"] ?? "Ошибка завершения регистрации";
                            $stage = 'link';
                        }
                    }
                }
            }
        }
    }
}
?>
<!DOCTYPE html>
<html>
<head>
    <title>Регистрация - OldMarket</title>
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-image: url(background.jpg); background-repeat: repeat; background-size: 5%; color: white; font-family: Arial; }
        .register-form { max-width: 340px; margin: 50px auto; padding: 20px; background: #4444445e; }
        input { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #a0b532; color: white; border: none; cursor: pointer; }
        .requirements { font-size: 12px; color: #aaa; margin-bottom: 10px; }
        .code-box { background: #222; padding: 10px; margin: 10px 0; font-size: 22px; text-align: center; letter-spacing: 2px; }
        a { color: #a0b532; }
    </style>
</head>
<body>

<div class="register-form">
    <h2>Регистрация</h2>

    <?php if ($error): ?>
        <p style="color:red"><?= $error ?></p>
    <?php endif; ?>

    <?php if ($stage === 'form'): ?>
        <div class="requirements">
            - Логин: 3–15 символов, только латиница и цифры<br>
            - Email корректный<br>
            - Пароль минимум 6 символа<br>
            - Telegram обязателен для регистрации
        </div>

        <form method="POST">
            <input type="hidden" name="action" value="start">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Далее</button>
        </form>
    <?php else: ?>
        <p>Шаг 2. Привяжите Telegram.</p>
        <p>Откройте бота @oldmarketsupport_bot и отправьте команду:</p>

        <div class="code-box">/link <?= htmlspecialchars($link_code) ?></div>

        <p>После этого нажмите кнопку ниже.</p>

        <form method="POST">
            <input type="hidden" name="action" value="check">
            <input type="hidden" name="code" value="<?= htmlspecialchars($link_code) ?>">
            <button type="submit">Проверить привязку</button>
        </form>

        <p style="margin-top:10px;">
            <a href="register.php">Начать заново</a>
        </p>
    <?php endif; ?>

    <p>Уже есть аккаунт? <a href="login.php">Войти</a></p>
</div>

</body>
</html>