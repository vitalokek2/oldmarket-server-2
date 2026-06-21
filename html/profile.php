<?php
require_once 'android_versions.php';
require_once __DIR__ . '/auth_cookie.php';
$auth = auth_user();

$profile_user_id = isset($_GET['user_id']) ? (int)$_GET['user_id'] : 0;
$logged_in_user_id = $auth ? (int)$auth['user_id'] : 0;

if ($profile_user_id <= 0) {
    if ($logged_in_user_id > 0) $profile_user_id = $logged_in_user_id;
    else {
        header("Location: index.php");
        exit;
    }
}

$is_logged_in = ($logged_in_user_id > 0);
$is_own_profile = ($is_logged_in && $profile_user_id === $logged_in_user_id);

$backUrl = 'index.php';
if (isset($_GET['return'])) {
    $ret = (string)$_GET['return'];
    $ret = str_replace(["\r", "\n"], "", $ret);

    if (strpos($ret, 'http://') === false && strpos($ret, 'https://') === false && strpos($ret, '//') !== 0) {
        if (preg_match('/^[a-zA-Z0-9_\-\/\.\?\=\&\#]+$/', $ret)) {
            $backUrl = $ret;
        }
    }
}

$profile = null;
$profile_response = @file_get_contents("http://94.156.115.120:5000/api/user/$profile_user_id/profile");
if ($profile_response !== FALSE) {
    $profile = json_decode($profile_response, true);
}
if (!$profile || isset($profile['error'])) {
    header("Location: index.php");
    exit;
}

$avatars = [];
if ($is_own_profile) {
    $avatars_response = @file_get_contents("http://94.156.115.120:5000/api/avatars");
    if ($avatars_response !== FALSE) {
        $avatars = json_decode($avatars_response, true) ?: [];
    }
}


$tgLinkData = null;
$tgError = '';

if ($is_own_profile) {
    $tgStatusResponse = @file_get_contents("http://94.156.115.120:5000/api/user/$profile_user_id/telegram-link");
    if ($tgStatusResponse !== FALSE) {
        $tgLinkData = json_decode($tgStatusResponse, true);
    }

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['start_tg_link'])) {
        $opts = [
            'http' => [
                'method'  => 'POST',
                'header'  => "Content-Type: application/json\r\n",
                'content' => '{}',
                'ignore_errors' => true
            ]
        ];

        $ctx = stream_context_create($opts);
        $startResponse = @file_get_contents(
            "http://94.156.115.120:5000/api/user/$profile_user_id/telegram-link/start",
            false,
            $ctx
        );

        if ($startResponse !== FALSE) {
            $tgLinkData = json_decode($startResponse, true);
            if (!is_array($tgLinkData)) {
                $tgLinkData = null;
                $tgError = "Не удалось получить ответ от сервера";
            }
        } else {
            $tgError = "Ошибка соединения с сервером";
        }
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $is_own_profile) {
    $new_avatar = isset($_POST['avatar']) ? (string)$_POST['avatar'] : '';
    $new_description = trim(isset($_POST['description']) ? (string)$_POST['description'] : '');

    $data = [
        'avatar' => $new_avatar,
        'description' => $new_description
    ];

    $options = [
        'http' => [
            'header'  => "Content-type: application/json\r\n",
            'method'  => 'PUT',
            'content' => json_encode($data, JSON_UNESCAPED_UNICODE),
            'ignore_errors' => true
        ]
    ];

    $context = stream_context_create($options);
    $result = @file_get_contents("http://94.156.115.120:5000/api/user/$profile_user_id/profile", false, $context);

    if ($result !== FALSE) {
        $response = json_decode($result, true);
        if (isset($response['success']) && $response['success']) {
            auth_set_cookies($profile_user_id, $auth['username'], $new_avatar, (int)$auth['is_premium']);

            $redir = "profile.php?user_id=" . $profile_user_id;
            if (!empty($_GET['return'])) $redir .= "&return=" . urlencode($_GET['return']);
            header("Location: " . $redir);
            exit;
        } else {
            $error = isset($response['error']) ? $response['error'] : "Ошибка при обновлении профиля";
        }
    } else {
        $error = "Ошибка соединения с сервером";
    }
}
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Профиль - <?= htmlspecialchars($profile['username']) ?></title>
    <style>
        body { background-image: url(background.jpg); background-repeat: repeat; background-size: 5%; color: white; font-family: Arial; }
        .profile-container { max-width: 500px; margin: 20px auto; padding: 20px; background: #4444445e; }
        .avatar { width: 100px; height: 100px; border-radius: 50%; margin: 0 auto; display: block; }
        .username { text-align: center; font-size: 24px; margin: 10px 0; }
        .description { text-align: center; margin: 10px 0; color: #ccc; }
        .avatar-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 20px 0; }
        .avatar-option { width: 50px; height: 50px; border-radius: 50%; cursor: pointer; }
        .avatar-option.selected { border: 3px solid #a0b532; }
        textarea { width: 100%; height: 100px; padding: 10px; margin: 10px 0; }
        button { padding: 10px 20px; background: #a0b532; color: white; border: none; cursor: pointer; }
        .back-btn { margin-bottom: 20px; color: #a0b532; text-decoration: none; display:inline-block; }
        .join-date { text-align:center; color:#ddd; }
        .telegram-box { margin-top: 20px; padding: 15px; background: #ffffff14; border: 1px solid #ffffff24; }
        .telegram-title { font-size: 18px; margin: 0 0 10px 0; }
        .telegram-btn { padding: 10px 20px; background: #54c8d5; color: white; border: none; cursor: pointer; }
        .telegram-code-wrap { margin-top: 10px; }
        .telegram-code { display: inline-block; padding: 8px 12px; background: #222; color: #fff; font-family: monospace; font-size: 18px; }
        .telegram-note { color: #ddd; margin-top: 8px; }
        .telegram-username { display: inline-block; padding: 8px 12px; background: #222; color: #fff; }
    </style>
</head>
<body>
    <div class="profile-container">
        <a href="<?= htmlspecialchars($backUrl) ?>" class="back-btn">← Назад</a>

        <img src="http://94.156.115.120:5000/html/avatars/<?= htmlspecialchars($profile['avatar']) ?>" class="avatar" alt="">
        <h2 class="username"><?= htmlspecialchars($profile['username']) ?></h2>
        <p class="description"><?= htmlspecialchars($profile['description']) ?></p>
        <p class="join-date">На сайте с: <?= htmlspecialchars($profile['created_at']) ?></p>


        <?php if ($is_own_profile): ?>
        <div class="telegram-box">
            <h3 class="telegram-title">Telegram</h3>

            <?php if (is_array($tgLinkData) && !empty($tgLinkData['linked'])): ?>
                <div class="telegram-username">
                    <?= htmlspecialchars(!empty($tgLinkData['tg_username']) ? '@' . ltrim($tgLinkData['tg_username'], '@') : 'Telegram привязан') ?>
                </div>
            <?php else: ?>
                <form method="POST" style="margin: 0;">
                    <button type="submit" name="start_tg_link" class="telegram-btn">Привязать аккаунт к Telegram боту</button>
                </form>

                <?php if (is_array($tgLinkData) && !empty($tgLinkData['code'])): ?>
                    <div class="telegram-code-wrap">
                        <div class="telegram-note">Отправьте боту эту команду:</div>
                        <div class="telegram-code">/link <?= htmlspecialchars($tgLinkData['code']) ?></div>
                        <div class="telegram-note">Код действует 30 минут.</div>
                    </div>
                <?php endif; ?>

                <?php if (!empty($tgError)): ?>
                    <p style="color: #ff8a8a;"><?= htmlspecialchars($tgError) ?></p>
                <?php elseif (is_array($tgLinkData) && !empty($tgLinkData['error'])): ?>
                    <p style="color: #ff8a8a;"><?= htmlspecialchars($tgLinkData['error']) ?></p>
                <?php endif; ?>
            <?php endif; ?>
        </div>
        <?php endif; ?>

        <?php if ($is_own_profile): ?>
        <hr>
        <h3>Редактировать профиль</h3>

        <?php if (isset($error)): ?>
            <p style="color: red;"><?= htmlspecialchars($error) ?></p>
        <?php endif; ?>

        <form method="POST">
            <h4>Выберите аватар:</h4>
            <div class="avatar-grid">
                <?php foreach ($avatars as $avatar): ?>
                <label>
                    <input type="radio" name="avatar" value="<?= htmlspecialchars($avatar) ?>"
                           <?= $avatar == $profile['avatar'] ? 'checked' : '' ?> style="display:none;">
                    <img src="http://94.156.115.120:5000/html/avatars/<?= htmlspecialchars($avatar) ?>"
                         class="avatar-option <?= $avatar == $profile['avatar'] ? 'selected' : '' ?>"
                         onclick="selectAvatar(this);">
                </label>
                <?php endforeach; ?>
            </div>

            <h4>Описание:</h4>
            <textarea name="description" placeholder="Расскажите о себе..." maxlength="200"><?= htmlspecialchars($profile['description']) ?></textarea>

            <button type="submit">Сохранить</button>
        </form>
        <?php endif; ?>
    </div>

<script type="text/javascript">
function selectAvatar(imgEl){
    var parent = imgEl.parentNode;
    var input = parent.getElementsByTagName('input')[0];
    if (input) input.checked = true;

    var els = document.getElementsByClassName('avatar-option');
    for (var i=0; i<els.length; i++){
        els[i].className = els[i].className.replace(' selected', '');
    }

    if (imgEl.className.indexOf('selected') === -1) imgEl.className += ' selected';
}
</script>
</body>
</html>
