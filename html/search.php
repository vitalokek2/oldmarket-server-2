<?php
require_once __DIR__ . '/auth_cookie.php';
require_once __DIR__ . '/site_ui.php';
require_once 'android_versions.php';

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$auth = auth_user();
$q = isset($_GET['q']) ? trim($_GET['q']) : '';

$searchUrl = '/api/apps/search';
if ($q !== '') {
    $searchUrl .= '?q=' . rawurlencode($q) . '&limit=200';
} else {
    $searchUrl .= '?limit=200';
}

$apiResponse = api_get($searchUrl);
$allApps = $apiResponse ? json_decode($apiResponse, true) : [];
if (!is_array($allApps)) $allApps = [];

$apps = $allApps;

$bannerResponse = api_get('/api/banners');
$banners = $bannerResponse ? json_decode($bannerResponse, true) : [];
if (!is_array($banners)) $banners = [];
?>
<!DOCTYPE html>
<html lang="<?= htmlspecialchars(om_lang()) ?>">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <title>Поиск приложений - OldMarket</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<?php render_site_header($auth, "index.php", false); ?>
<div class="search-container">
    <form method="get" action="search.php" style="margin:0;">
      <input type="text" id="searchInput" name="q" placeholder="<?= htmlspecialchars(om_t("Поиск", "Search")) ?>" value="<?= htmlspecialchars($q) ?>">
    </form>
  </div>
<script>
  function installApp(appId) {
    window.location.href = 'app.php?id=' + appId;
  }
</script>

<main>
  <section class="featured">
    <h2 style="color: white; text-align: center;"><?= htmlspecialchars(om_t("Поиск приложений", "App search")) ?></h2>

    <div style="text-align:center; color:#d0d0d0; margin-bottom: 20px;">
      <?php if ($q !== ''): ?>
        <?= htmlspecialchars(om_t("Результаты по запросу", "Results for")) ?>: <strong><?= htmlspecialchars($q) ?></strong>
      <?php else: ?>
        <?= htmlspecialchars(om_t("Введите название приложения в строке поиска", "Enter an app name in the search field")) ?>
      <?php endif; ?>
    </div>

    <div class="app-list">
      <?php if ($q === ''): ?>
        <div style="width:100%; text-align:center; color:white; padding: 20px 10px;">
          <?= htmlspecialchars(om_t("Начните вводить запрос в поиск.", "Start typing your search query.")) ?>
        </div>
      <?php elseif (empty($apps)): ?>
        <div style="width:100%; text-align:center; color:white; padding: 20px 10px;">
          <?= htmlspecialchars(om_t("Ничего не найдено.", "Nothing found.")) ?>
        </div>
      <?php else: ?>
        <?php foreach ($apps as $app): ?>
        <div class="app" onclick="installApp(<?= $app['id'] ?>)">
          <img src="http://oldmarket.store:5000/html/apps/<?= $app['icon'] ?>" width="55">
          <div class="app-info">
            <span class="app-title"><?= htmlspecialchars($app['name']) ?></span><br>
            <span><?= htmlspecialchars(om_t("Рейтинг", "Rating")) ?>: <?= $app['rating'] ?> ★</span><br>
            <span><?= htmlspecialchars(om_t("Скачиваний", "Downloads")) ?>: <?= $app['downloads'] ?></span><br>
            <span>Android <?= apiToAndroidVersion($app['api']) ?></span>
          </div>
        </div>
        <?php endforeach; ?>
      <?php endif; ?>
    </div>
  </section>
</main>
<div class="footer">
  <p>OldMarket &copy; 2025-2026</p>
</div>
</body>
</html>
