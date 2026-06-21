<?php 
require_once 'android_versions.php';
require_once __DIR__ . '/auth_cookie.php';
$auth = auth_user();

$appId = isset($_GET['id']) ? (int)$_GET['id'] : 0;
if ($appId <= 0) {
    header("Location: index.php");
    exit;
}

$appData = null;
$appResponse = @file_get_contents("http://94.156.115.120:5000/api/app/$appId");
if ($appResponse !== FALSE) {
    $appData = json_decode($appResponse, true);
}

if (!$appData || isset($appData['error'])) {
    header("Location: index.php");
    exit;
}

$backUrl = 'index.php'; 

if (!empty($appData['is_game'])) {
    $backUrl = 'index.php';
}

$categoryLabels = [
    'system_utilites' => 'Системные утилиты',
    'video_hosting' => 'Видеохостинги',
    'social_network' => 'Социальные сети',
    'messenger' => 'Мессенджеры',
    'browsers' => 'Браузеры',
    'news' => 'Новости',
    'maps' => 'Карты',
    'bank' => 'Банки',
    'music' => 'Музыка',
    'music_players' => 'Аудиоплееры',
    'video_players' => 'Видеоплееры',
    'office' => 'Офис',
    'weather' => 'Погода',
    'vpn' => 'VPN',
    'personalization' => 'Персонализация',
    'education' => 'Обучение',
    'video_editor' => 'Видеоредакторы',
    'photo' => 'Фото',
    'launcher' => 'Лаунчеры',
    'emulators' => 'Эмуляторы',
    'keyboard' => 'Клавиатура',
    'screen_recorder' => 'Запись экрана',
    'clock' => 'Часы',
    'ai' => 'AI',
    'camera' => 'Камера',
    'disk' => 'Облако',
    'mail' => 'Почта',
    'others' => 'Другие',
    'simulators' => 'Симуляторы',
    'puzzles' => 'Головоломки',
    'arcade' => 'Аркада',
    'races' => 'Гонки',
    'action_games' => 'Экшен',
    'casual' => 'Казуальные',
    'strategies' => 'Стратегии',
    'table_games' => 'Настольные игры',
    'shooter' => 'Шутеры',
    'horror' => 'Хоррор',
    'adventures' => 'Приключения',
    'rpg' => 'РПГ',
    'survival' => 'Выживание',
    'sport' => 'Спорт',
    'card_games' => 'Карточные игры',
    'other_games' => 'Другие игры'
];

$appAuthor = '';
if (isset($appData['author'])) {
    $appAuthor = trim((string)$appData['author']);
}

$categoryCode = '';
if (isset($appData['category_code'])) {
    $categoryCode = trim((string)$appData['category_code']);
} elseif (isset($appData['category'])) {
    $categoryCode = trim((string)$appData['category']);
}

$appCategory = '';
if ($categoryCode !== '') {
    $appCategory = isset($categoryLabels[$categoryCode]) ? $categoryLabels[$categoryCode] : $categoryCode;
}

$bad_words = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['submit_review'])) {

    if (!$auth) { header("Location: login.php"); exit; }
    $user_id = (int)$auth['user_id'];
    $rating = (int)$_POST['rating'];
    $comment = trim($_POST['comment']);

    $errors = [];

    if ($rating < 1 || $rating > 5) {
        $errors[] = "Рейтинг должен быть от 1 до 5 звезд";
    }

    if (!empty($comment)) {
        if (strlen($comment) > 300) {
            $errors[] = "Отзыв не должен превышать 300 символов";
        }

        if (!preg_match('/^[a-zA-Zа-яА-ЯёЁ0-9\s\ї\Ї\ґ\Ґ\є\Є\!\(\)\?\.\,\-\:\;\"]+$/u', $comment)) {
            $errors[] = "Отзыв содержит запрещённые символы";
        }

        $comment_lower = strtolower($comment);
        foreach ($bad_words as $bad_word) {
            if (strpos($comment_lower, $bad_word) !== false) {
                $errors[] = "Отзыв содержит недопустимые слова";
                break;
            }
        }
    }

    if (empty($errors)) {
        $ip = $_SERVER['REMOTE_ADDR'];
        if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
            $ip = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR'])[0];
        }

        $data = [
            'user_id' => $user_id,
            'rating' => $rating,
            'comment' => $comment,
            'ip' => $ip
        ];

        $options = [
            'http' => [
                'header'  => "Content-type: application/json\r\n",
                'method'  => 'POST',
                'content' => json_encode($data),
                'ignore_errors' => true
            ]
        ];

        $context = stream_context_create($options);
        $result = @file_get_contents("http://94.156.115.120:5000/api/app/$appId/review", false, $context);

        if ($result !== FALSE) {
            $response = json_decode($result, true);
            if (isset($response['success']) && $response['success']) {
                header("Location: app.php?id=" . $appId);
                exit;
            } else {
                $error = $response['error'] ?? "Ошибка при добавлении отзыва";
            }
        } else {
            $error = "Ошибка соединения с сервером";
        }
    } else {
        $error = implode("<br>", $errors);
    }
}

$reviews = [];
$viewerId = $auth ? (int)$auth['user_id'] : 0;
$reviewsUrl = "http://94.156.115.120:5000/api/app/$appId/reviews" . ($viewerId ? "?viewer_id=$viewerId" : "");
$reviewsResponse = @file_get_contents($reviewsUrl);
if ($reviewsResponse !== FALSE) {
    $reviews = json_decode($reviewsResponse, true) ?: [];
}

$userHasReviewed = false;
if ($auth) {
    foreach ($reviews as $review) {
        if ((int)($review['user_id'] ?? 0) === (int)$auth['user_id']) {
            $userHasReviewed = true;
            break;
        }
    }
}

$screenshots = [];
$screenshots_response = @file_get_contents("http://94.156.115.120:5000/api/app/$appId/screenshots");
if ($screenshots_response !== FALSE) {
    $screenshots = json_decode($screenshots_response, true) ?: [];
}

$versions = [];
$versions_response = @file_get_contents("http://94.156.115.120:5000/api/app/$appId/versions");
if ($versions_response !== FALSE) {
    $versions = json_decode($versions_response, true) ?: [];
}

if (empty($versions)) {
    $versions[] = [
        'version' => $appData['version'],
        'apk_file' => $appData['apk_file'],
        'api' => $appData['api']
    ];
}
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OldMarket - <?= htmlspecialchars($appData['name']) ?></title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background-size: cover;
            color: #fff;
        }

        .header-bar {
            background-image: url(background.jpg);
            background-repeat: repeat;
            background-size: 20%;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 5px 16px;
        }

        .back-btn { font-size: 22px; margin-right: 10px; }

        .store-icon { width: 42px; height: 42px; }
        .back-icon { width: 20px; height: 25px; cursor: pointer; }
        
        .header-title { display: flex; align-items: center; }
        .header-icons { display: flex; gap: 15px; }
        .icon { font-size: 26px; cursor: pointer; }

        .main-info {
            background: #444;
            display: flex;
            align-items: center;
            padding: 18px 10px;
        }

        .app-logo { width: 50px; height: 50px; margin-right: 18px; }

        .app-text { flex: 1; }
        .main-title { font-size: 20px; font-weight: bold; }

        .app-author {
            color: #a6a6a6;
            font-weight: bold;
            font-size: 12px;
            margin-top: 3px;
        }

        .install-btn {
            background: #54c8d5;
            color: #fff;
            border: none;
            font-size: 21px;
            cursor: pointer;
            margin-left: 15px;
            padding: 10px 20px;
            text-decoration: none;
            display: inline-block;
        }

        .screenshots {
            display: flex;
            background: url('appdownload/screenback.png');
            background-repeat: repeat;
            background-size: 6%;
            align-items: flex-start;
            padding: 22px 0;
            gap: 24px;
            flex-wrap: wrap;
        }

        .screen {
            width: 200px;
            height: 355px;
            object-fit: cover;
            background: #ddd;
            border: 8px solid #ccc;
        }

        .description {
            color: #000000;
            text-align: left;
            margin-top: 10px;
            font-size: 16px;
            padding: 10px;
            background: white;
        }

        .reviews-section {
            background: #444444;
            padding: 20px;
            margin-top: 20px;
        }
        
        .review {
            background: white;
            padding: 15px;
            margin: 10px 0;
            color: #333;
        }
        
        .review-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .review-header a {
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            color: #333;
        }

        .review-header a:hover { text-decoration: underline; }

        .review-header img {
            border-radius: 50%;
            object-fit: cover;
        }

        .review-rating {
            color: gold;
            font-weight: bold;
            font-size: 18px;
        }
        
        .add-review {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
            color: #333;
        }
        
        .star-rating { direction: rtl; unicode-bidi: bidi-override; }
        .star-rating input { display: none; }
        .star-rating label { font-size: 24px; color: #ccc; cursor: pointer; }
        .star-rating input:checked ~ label,
        .star-rating label:hover,
        .star-rating label:hover ~ label { color: gold; }

        .user-section { color: white; }
        .user-section a { color: white; text-decoration: none; }

        .version-selector {
            display: flex;
            gap: 10px;
            margin-left: 20px;
        }

        .version-selector select {
            padding: 10px;
            font-size: 16px;
            border: 2px solid #a0b532;
            background: white;
            color: #333;
        }

        .screen:hover { transform: scale(1.05); }

        .reactions-row{
            display:flex;
            align-items:center;
            gap:10px;
            margin-top:10px;
            flex-wrap:wrap;
        }

        .react-btn{
            border:1px solid #ccc;
            background:#f3f3f3;
            padding:6px 10px;
            cursor:pointer;
            font-size:14px;
            display:inline-flex;
            align-items:center;
            gap:6px;
        }

        .react-icon{
            width:16px;
            height:16px;
            display:inline-block;
        }

        .react-btn.active{
            border-color:#54c8d5;
            background:#e6fbff;
        }

        .comments-toggle{
            cursor:pointer;
            color:#1d6fdc;
            font-size:14px;
        }

        .comments-box{
            margin-top:10px;
            padding:10px;
            background:#fafafa;
            border:1px solid #ddd;
            display:none;
        }

        .comment-item{
            padding:8px 0;
            border-bottom:1px solid #eee;
            display:flex;
            gap:10px;
            align-items:flex-start;
        }

        .comment-item:last-child{ border-bottom:none; }

        .comment-avatar{
            width:28px;
            height:28px;
            border-radius:50%;
            object-fit:cover;
            flex:0 0 auto;
        }

        .comment-body{ flex:1; }

        .comment-meta{
            font-size:12px;
            color:#666;
        }

        .comment-text{
            margin:4px 0 0 0;
            font-size:14px;
            color:#333;
            word-wrap:break-word;
        }

        .comment-form{
            margin-top:10px;
            display:flex;
            gap:8px;
        }

        .comment-form input{
            flex:1;
            padding:8px;
            border:1px solid #ccc;
        }

        .comment-form button{
            padding:8px 12px;
            border:none;
            background:#a0b532;
            color:white;
            cursor:pointer;
        }
        a.install-btn{
            background: #54c8d5 !important;
            color: #fff !important;
            text-decoration: none !important;
            border: none !important;
            display: inline-block !important;
            padding: 10px 20px !important;
            font-size: 21px !important;
        }
        @media (max-width: 320px) {
            .main-title { font-size: 20px; }
            .install-btn { padding: 8px 16px; font-size: 18px; }
            .screen { width: 150px; height: 267px; }
        }

        @media (max-width: 480px) {
            .main-title { font-size: 18px; }
            .install-btn { padding: 6px 12px; font-size: 16px; }
            .screen { width: 130px; height: 232px; }
            .back-btn { font-size: 18px; }
            .store-icon { width: 32px; height: 32px; }
            .back-icon { width: 20px; height: 25px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="header-bar">
            <div class="header-title">
                <img src="appdownload/back.png"
                    alt="Back"
                    class="back-icon"
                    onclick="window.location.href='<?= htmlspecialchars($backUrl) ?>'">
                <img src="appdownload/store.png" alt="Store" class="store-icon">
            </div>
            <div class="user-section">
                <?php if ($auth): ?>
                    Привет, <?= htmlspecialchars($auth['username']) ?>
                <?php else: ?>
                    <a href="login.php">Войдите</a> чтобы оставить отзыв
                <?php endif; ?>
            </div>
        </div>

        <div class="main-info">
            <img src="http://94.156.115.120:5000/html/apps/<?= $appData['icon'] ?>" alt="app-logo" class="app-logo">
            <div class="app-text">
                <span class="main-title"><?= htmlspecialchars($appData['name']) ?></span>
                <?php if ($appAuthor !== ''): ?>
                    <div class="app-author"><?= htmlspecialchars($appAuthor) ?></div>
                <?php endif; ?>
            </div>
            <a id="downloadLink" class="install-btn" href="http://94.156.115.120:5000/api/download/<?= (int)$appData['id'] ?><?= $auth ? '?user_id='.(int)$auth['user_id'] : '' ?>">Установить</a>
        </div>
    </header>

    <main>
        <?php if (!empty($screenshots)): ?>
        <div class="screenshots">
            <div style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
                <?php foreach ($screenshots as $screenshot): ?>
                <img src="http://94.156.115.120:5000/html/screenshots/<?= $screenshot ?>" class="screen"
                    onclick="openModal('http://94.156.115.120:5000/html/screenshots/<?= $screenshot ?>')">
                <?php endforeach; ?>
            </div>
        </div>
        <?php endif; ?>

        <div class="description">
            <p><strong>Описание:</strong></p>
            <p><?= htmlspecialchars($appData['description']) ?></p>
            <p><strong>Версия:</strong> <?= $appData['version'] ?></p>
            <p><strong>Android:</strong> <?= apiToAndroidVersion($appData['api']) ?></p>
            <p><strong>Рейтинг:</strong> <?= $appData['rating'] ?> ★ (<?= $appData['review_count'] ?> отзывов)</p>
            <p><strong>Скачиваний:</strong> <?= $appData['downloads'] ?></p>
            <?php if ($appCategory !== ''): ?>
            <p><strong>Категория:</strong> <?= htmlspecialchars($appCategory) ?></p>
            <?php endif; ?>
            <p><strong>Имя пакета:</strong> <?= htmlspecialchars($appData['package']) ?></p>
        </div>

        <div class="version-selector">
            <select id="versionSelect" onchange="updateDownloadLink()">
                <?php foreach ($versions as $version): ?>
                <option value="<?= htmlspecialchars($version['version']) ?>" 
                        data-apk="<?= htmlspecialchars($version['apk_file']) ?>"
                        data-api="<?= htmlspecialchars($version['api']) ?>"
                        <?= $version['version'] == $appData['version'] ? 'selected' : '' ?>>
                    Версия <?= htmlspecialchars($version['version']) ?> (Android <?= apiToAndroidVersion($version['api']) ?>)
                </option>
                <?php endforeach; ?>
            </select>
        </div>

        <?php if ($auth && !$userHasReviewed): ?>
        <div class="add-review">
            <h3>Оставить отзыв</h3>
            <?php if (isset($error)): ?>
                <div style="color: red; margin-bottom: 10px;"><?= $error ?></div>
            <?php endif; ?>
            
            <form method="POST">
                <input type="hidden" name="user_id" value="<?= (int)$auth['user_id'] ?>">
                
                <div class="star-rating">
                    <input type="radio" id="star5" name="rating" value="5" required><label for="star5">★</label>
                    <input type="radio" id="star4" name="rating" value="4"><label for="star4">★</label>
                    <input type="radio" id="star3" name="rating" value="3"><label for="star3">★</label>
                    <input type="radio" id="star2" name="rating" value="2"><label for="star2">★</label>
                    <input type="radio" id="star1" name="rating" value="1"><label for="star1">★</label>
                </div>
                
                <textarea name="comment" placeholder="Ваш отзыв (максимум 300 символов)..." 
                        style="width: 100%; height: 100px; margin: 10px 0;" 
                        maxlength="300"><?= isset($_POST['comment']) ? htmlspecialchars($_POST['comment']) : '' ?></textarea>
                
                <button type="submit" name="submit_review" style="padding: 10px 20px; background: #a0b532; color: white; border: none;">Отправить</button>
            </form>
        </div>
        <?php elseif (isset($_SESSION['user_id'])): ?>
        <div class="add-review">
            <p>Вы уже оставили отзыв для этого приложения.</p>
        </div>
        <?php endif; ?>

        <div class="reviews-section" id="reviews">
            <h3>Отзывы (<?= count($reviews) ?>)</h3>

            <?php if (empty($reviews) || isset($reviews['error'])): ?>
                <p>Пока нет отзывов. Будьте первым!</p>
            <?php else: ?>
                <?php foreach ($reviews as $review): ?>
                <?php
                    $rid = (int)($review['id'] ?? 0);
                    $likes = (int)($review['likes'] ?? 0);
                    $dislikes = (int)($review['dislikes'] ?? 0);
                    $userReaction = (int)($review['user_reaction'] ?? 0); // 1, -1, 0
                    $commentsCount = (int)($review['comments_count'] ?? 0);
                ?>
                <div class="review" id="reviews">
                    <div class="review-header">
                        <a href="profile.php?user_id=<?= (int)$review['user_id'] ?>&return=<?= urlencode('app.php?id='.(int)$appId.'#reviews') ?>" style="text-decoration: none; color: #333; display: flex; align-items: center; gap: 10px;">
                            <img src="http://94.156.115.120:5000/html/avatars/<?= htmlspecialchars($review['avatar'] ?? 'default_avatar.png') ?>" 
                                width="40" height="40" style="border-radius: 50%;">
                            <strong><?= htmlspecialchars($review['username'] ?? 'Unknown') ?></strong>
                        </a>
                        <span class="review-rating"><?= str_repeat('★', (int)($review['rating'] ?? 0)) ?></span>
                    </div>

                    <p><?= htmlspecialchars($review['comment'] ?? '') ?></p>
                    <small><?= htmlspecialchars($review['created_at'] ?? '') ?></small>

                    <div class="reactions-row"
                        data-review-id="<?= $rid ?>"
                        data-user-reaction="<?= $userReaction ?>">

                        <button class="react-btn like-btn <?= $userReaction === 1 ? 'active' : '' ?>"
                                onclick="setReaction(<?= $rid ?>, 1)">
                            <img class="react-icon" src="like.png" alt="like">
                            <span class="like-count"><?= $likes ?></span>
                        </button>

                        <button class="react-btn dislike-btn <?= $userReaction === -1 ? 'active' : '' ?>"
                                onclick="setReaction(<?= $rid ?>, -1)">
                            <img class="react-icon" src="dislike.png" alt="dislike">
                            <span class="dislike-count"><?= $dislikes ?></span>
                        </button>
                        
                        <?php if ($auth): ?>
                        <button type="button" class="react-btn" onclick="reportReview(<?= $rid ?>)">
                            🚩 Жалоба
                        </button>
                        <?php endif; ?>
                        <span class="comments-toggle" onclick="toggleComments(<?= $rid ?>)">
                            Комментарии (<span class="comments-count"><?= $commentsCount ?></span>)
                        </span>
                    </div>

                    <div class="comments-box" id="commentsBox-<?= $rid ?>">
                        <div id="commentsList-<?= $rid ?>">Загрузка...</div>

                        <?php if ($auth): ?>
                        <div class="comment-form">
                            <input type="text" id="commentInput-<?= $rid ?>" maxlength="300"
                                placeholder="Написать комментарий (до 300 символов)">
                            <button type="button" onclick="addComment(<?= $rid ?>)">Отправить</button>
                        </div>
                        <?php else: ?>
                            <div style="margin-top:10px; font-size: 14px; color:#555;">
                                <a href="login.php">Войдите</a>, чтобы комментировать.
                            </div>
                        <?php endif; ?>
                    </div>
                </div>
                <?php endforeach; ?>
            <?php endif; ?>
        </div>
    </main>

    <div id="screenshotModal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,.8); align-items:center; justify-content:center; z-index:9999;">
        <img id="modalImage" src="" style="max-width:90%; max-height:90%; border:6px solid #fff;">
    </div>
    
<script type="text/javascript">
var API_BASE = 'http://94.156.115.120:5000';
var CURRENT_USER_ID = <?= $auth ? (int)$auth['user_id'] : 0 ?>;

function byId(id) {
    return document.getElementById(id);
}

function updateDownloadLink() {
    var select = byId('versionSelect');
    if (!select) return;

    var selectedOption = select.options[select.selectedIndex];
    var version = selectedOption.value;

    var downloadLink = byId('downloadLink');
    if (!downloadLink) return;

    downloadLink.href = 'http://94.156.115.120:5000/api/download/<?= (int)$appData['id'] ?>/' +
        encodeURIComponent(version) +
        '<?= $auth ? '?user_id=' . (int)$auth['user_id'] : '' ?>';
}

function openModal(imageSrc) {
    var modalImage = byId('modalImage');
    var modal = byId('screenshotModal');
    if (!modalImage || !modal) return;

    modalImage.src = imageSrc;
    modal.style.display = 'flex';
}

function closeModal() {
    var modal = byId('screenshotModal');
    if (!modal) return;
    modal.style.display = 'none';
}

(function(){
    var modal = byId('screenshotModal');
    if (!modal) return;

    if (modal.addEventListener) {
        modal.addEventListener('click', function(e) {
            e = e || window.event;
            var target = e.target || e.srcElement;
            if (target && target.id === 'screenshotModal') closeModal();
        });
    } else if (modal.attachEvent) {
        modal.attachEvent('onclick', function(e) {
            e = e || window.event;
            var target = e.target || e.srcElement;
            if (target && target.id === 'screenshotModal') closeModal();
        });
    }
})();

function findReviewRow(reviewId) {
    var rows = document.getElementsByClassName('reactions-row');
    for (var i = 0; i < rows.length; i++) {
        var rid = parseInt(rows[i].getAttribute('data-review-id'), 10);
        if (rid === reviewId) return rows[i];
    }
    return null;
}

function ajaxJson(method, url, bodyObj, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true);

    if (method !== 'GET') {
        xhr.setRequestHeader('Content-Type', 'application/json');
    }

    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;

        var json = null;
        try { json = JSON.parse(xhr.responseText); } catch(e) {}

        cb(xhr.status, json, xhr.responseText);
    };

    xhr.send(bodyObj ? JSON.stringify(bodyObj) : null);
}

function setReaction(reviewId, value) {
    if (!CURRENT_USER_ID) {
        alert('Войдите, чтобы ставить реакции');
        return;
    }

    var row = findReviewRow(reviewId);
    if (!row) return;

    var current = parseInt(row.getAttribute('data-user-reaction') || '0', 10);
    var newValue = (current === value) ? 0 : value;

    ajaxJson('POST', API_BASE + '/api/review/' + reviewId + '/reaction', {
        user_id: CURRENT_USER_ID,
        value: newValue
    }, function(status, json) {
        if (status < 200 || status >= 300) {
            alert((json && json.error) ? json.error : ('Ошибка (' + status + ')'));
            return;
        }

        var likeCount = row.getElementsByClassName('like-count')[0];
        var dislikeCount = row.getElementsByClassName('dislike-count')[0];

        if (likeCount) likeCount.innerHTML = (json && json.likes != null) ? json.likes : 0;
        if (dislikeCount) dislikeCount.innerHTML = (json && json.dislikes != null) ? json.dislikes : 0;

        var likeBtn = row.getElementsByClassName('like-btn')[0];
        var dislikeBtn = row.getElementsByClassName('dislike-btn')[0];

        if (likeBtn) {
            likeBtn.className = likeBtn.className.replace(' active', '');
            if (json && json.user_reaction === 1) likeBtn.className += ' active';
        }
        if (dislikeBtn) {
            dislikeBtn.className = dislikeBtn.className.replace(' active', '');
            if (json && json.user_reaction === -1) dislikeBtn.className += ' active';
        }

        row.setAttribute('data-user-reaction', (json && json.user_reaction != null) ? json.user_reaction : 0);
    });
}

function reportReview(reviewId) {
    if (!CURRENT_USER_ID) {
        alert('Войдите, чтобы отправлять жалобы');
        return;
    }

    if (!confirm('Вы действительно хотите отправить жалобу?')) {
        return;
    }

    var reason = '';

    ajaxJson('POST', API_BASE + '/api/review/' + reviewId + '/report', {
        user_id: CURRENT_USER_ID,
        reason: reason
    }, function(status, json) {
        if (status < 200 || status >= 300) {
            alert((json && json.error) ? json.error : ('Ошибка (' + status + ')'));
            return;
        }
        alert('Жалоба отправлена модераторам');
    });
}

function toggleComments(reviewId) {
    var box = byId('commentsBox-' + reviewId);
    if (!box) return;

    var isOpen = (box.style.display === 'block');
    box.style.display = isOpen ? 'none' : 'block';

    if (!isOpen) {
        loadComments(reviewId);
    }
}

function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;')
        .replace(/'/g,'&#039;');
}

function loadComments(reviewId) {
    var list = byId('commentsList-' + reviewId);
    if (!list) return;

    list.innerHTML = 'Загрузка...';

    ajaxJson('GET', API_BASE + '/api/review/' + reviewId + '/comments', null, function(status, json) {
        if (status < 200 || status >= 300) {
            list.innerHTML = (json && json.error) ? escapeHtml(json.error) : ('Ошибка (' + status + ')');
            return;
        }

        if (!json || !json.length) {
            list.innerHTML = '<div style="color:#555;">Комментариев пока нет.</div>';
            return;
        }

        var html = '';
        for (var i = 0; i < json.length; i++) {
            var c = json[i];
            var avatar = c.avatar ? c.avatar : 'default_avatar.png';
            var username = c.username ? c.username : 'Unknown';
            var created = c.created_at ? c.created_at : '';
            var text = c.text ? c.text : '';

            html += ''
            + '<div class="comment-item">'
            +   '<img class="comment-avatar" src="' + API_BASE + '/html/avatars/' + encodeURIComponent(avatar) + '" alt="">'
            +   '<div class="comment-body">'
            +     '<div class="comment-meta"><strong>' + escapeHtml(username) + '</strong> • ' + escapeHtml(created) + '</div>'
            +     '<p class="comment-text">' + escapeHtml(text) + '</p>'
            +   '</div>'
            + '</div>';
        }
        list.innerHTML = html;
    });
}

function addComment(reviewId) {
    if (!CURRENT_USER_ID) {
        alert('Войдите, чтобы комментировать');
        return;
    }

    var input = byId('commentInput-' + reviewId);
    if (!input) return;

    var text = (input.value || '').replace(/^\s+|\s+$/g,'');
    if (!text) {
        alert('Введите комментарий');
        return;
    }

    ajaxJson('POST', API_BASE + '/api/review/' + reviewId + '/comment', {
        user_id: CURRENT_USER_ID,
        text: text
    }, function(status, json) {
        if (status < 200 || status >= 300) {
            alert((json && json.error) ? json.error : ('Ошибка (' + status + ')'));
            return;
        }

        input.value = '';
        loadComments(reviewId);

        var row = findReviewRow(reviewId);
        if (row) {
            var cc = row.getElementsByClassName('comments-count')[0];
            if (cc) {
                var n = parseInt(cc.innerHTML || '0', 10);
                cc.innerHTML = (n + 1);
            }
        }
    });
}
</script>
</body>
</html>