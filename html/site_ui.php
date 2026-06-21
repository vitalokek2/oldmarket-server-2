<?php
$__om_initial_lang = 'ru';
if (isset($_COOKIE['site_lang'])) {
    $__om_cookie_lang = strtolower(trim((string)$_COOKIE['site_lang']));
    if ($__om_cookie_lang === 'ru' || $__om_cookie_lang === 'en') {
        $__om_initial_lang = $__om_cookie_lang;
    }
}
if (isset($_GET['lang'])) {
    $__om_get_lang = strtolower(trim((string)$_GET['lang']));
    if ($__om_get_lang === 'ru' || $__om_get_lang === 'en') {
        $__om_initial_lang = $__om_get_lang;
        $_COOKIE['site_lang'] = $__om_get_lang;
        if (!headers_sent()) {
            setcookie('site_lang', $__om_get_lang, time() + 60 * 60 * 24 * 365, '/');
        }
    }
}

if (!function_exists('om_lang')) {
    function om_lang() {
        global $__om_initial_lang;
        $lang = strtolower(trim((string)$__om_initial_lang));
        return ($lang === 'en') ? 'en' : 'ru';
    }

    function om_is_en() { return om_lang() === 'en'; }

    function om_t($ru, $en) { return om_is_en() ? $en : $ru; }

    function om_img($name) {
        $dot = strrpos($name, '.');
        if (!om_is_en() || $dot === false) return $name;
        return substr($name, 0, $dot) . '_en' . substr($name, $dot);
    }

    function om_url_with_lang($url) {
        $lang = om_lang();
        if ($lang === 'ru') return $url;
        $sep = (strpos($url, '?') === false) ? '?' : '&';
        return $url . $sep . 'lang=' . rawurlencode($lang);
    }

    function om_profile_avatar($auth) {
        $avatar = (is_array($auth) && !empty($auth['avatar'])) ? $auth['avatar'] : 'default_avatar.png';
        if (defined('API_BASE')) {
            return API_BASE . '/html/avatars/' . htmlspecialchars($avatar);
        }
        return 'http://94.156.115.120:5000/html/avatars/' . htmlspecialchars($avatar);
    }

    function render_site_css() {
        ?>
        <style>
            .om-clear:after{content:"";display:block;clear:both;}
            .sticky-header-section,.topnav,.om-lang-switch{background:#2e2e2e url('background.jpg') repeat;background-size:5%;}
            .topnav{white-space:nowrap;margin:0;padding:2px 1px;}
            .topnav .logo,.topnav .om-search-in-logo{vertical-align:middle;}
            .topnav .logo{display:inline-block;}
            .om-search-in-logo{display:inline-block;margin-left:15px;}
            .om-search-icon{width:40px;height:40px;cursor:pointer;border:0;vertical-align:middle;}
            .user-section a,.om-profile-link{white-space:nowrap;}
            .om-button-panel{
                background:#2e2e2e url('background.jpg') repeat;
                background-size:5%;
                border-top:1px solid rgba(255,255,255,.12);
                border-bottom:1px solid rgba(0,0,0,.45);
                padding:5px 5px;
                font-family:Arial,sans-serif;
                white-space:nowrap;
                overflow:hidden;
            }
            .om-panel-table{display:table;width:100%;border-collapse:collapse;table-layout:fixed;}
            .om-panel-left,.om-panel-right{display:table-cell;vertical-align:middle;white-space:nowrap;}
            .om-panel-right{text-align:right;}
            .om-panel-btn,.om-profile-link,.om-logout-link{display:inline-block;vertical-align:middle;margin:0 5px;text-decoration:none;color:#fff;}
            .om-panel-img{display:block;border:0;max-height:30px;width:150px;}
            .om-profile-avatar{width:30px;height:30px;border-radius:50%;vertical-align:middle;margin-right:7px;}
            .om-profile-name{display:inline-block;vertical-align:middle;color:#fff;font-weight:bold;max-width:150px;overflow:hidden;text-overflow:ellipsis;}
            .om-lang-switch{padding:14px 10px;text-align:center;color:#ddd;font-family:Arial,sans-serif;border-top:1px solid rgba(255,255,255,.12);}
            .om-lang-switch a{color:#fff;text-decoration:none;display:inline-block;margin:0 4px;padding:5px 10px;background:#333;border:1px solid #555;}
            .om-lang-switch a.active{background:#a0b532;border-color:#a0b532;color:#fff;}
            .app,.main-info,.review-header,.reactions-row,.comment-form,.screenshots{min-width:0;}
            .app-info{min-width:0;word-wrap:break-word;overflow-wrap:break-word;}
            @media (max-width:480px){.om-panel-img{max-height:34px}.om-profile-name{max-width:95px}.om-panel-btn,.om-profile-link,.om-logout-link{margin:0 2px}.om-search-in-logo{margin-left:8px}.om-search-icon{width:36px;height:36px}}
        </style>
        <?php
    }

    function render_site_header($auth, $home_link, $show_panel = true) {
        render_site_css();
        ?>
        <div class="sticky-header-section om-clear">
          <header class="topnav om-clear">
            <div class="logo">
              <a href="<?= htmlspecialchars(om_url_with_lang($home_link)) ?>" style="text-decoration:none;"><img src="logo.png" alt="OldMarket" width="260"></a>
              <p id="visitorCount"; font-size: 0.8em;"></p>
            </div>
            <div padding:10px; text-align: right;">
                <div style="position: absolute; right: 10px; top: 10px;">
                    <img src="search.png"
                        alt="Поиск"
                        title="Поиск"
                        style="width: 40px; height: 40px; cursor: pointer;"
                        onclick="window.location.href='search.php'">
                </div>
            </div>
          </header>
          <?php if ($show_panel) render_site_panel($auth); ?>
        </div>
        <?php
    }

    function render_site_panel($auth) {
        $downloadImg = om_img('downloadclient.png');
        $registerImg = om_img('register.png');
        $loginImg = om_img('login.png');
        ?>
        <div class="om-button-panel">
          <div class="om-panel-table">
            <div class="om-panel-left">
              <a class="om-panel-btn" href="marketdownload.html"><img class="om-panel-img" src="<?= htmlspecialchars($downloadImg) ?>" alt="<?= htmlspecialchars(om_t('Скачать клиент','Download client')) ?>"></a>
            </div>
            <div class="om-panel-right">
              <?php if ($auth): ?>
                <a class="om-profile-link" href="profile.php"><img class="om-profile-avatar" src="<?= om_profile_avatar($auth) ?>" alt=""><span class="om-profile-name <?= (!empty($auth['is_premium'])) ? 'premium-user' : '' ?>"><?= htmlspecialchars(isset($auth['username']) ? $auth['username'] : '') ?></span></a>
                <a class="om-logout-link" href="logout.php"><?= htmlspecialchars(om_t('Выйти','Logout')) ?></a>
              <?php else: ?>
                <a class="om-panel-btn" href="register.php"><img class="om-panel-img" src="<?= htmlspecialchars($registerImg) ?>" alt="<?= htmlspecialchars(om_t('Регистрация','Register')) ?>"></a>
                <a class="om-panel-btn" href="login.php"><img class="om-panel-img" src="<?= htmlspecialchars($loginImg) ?>" alt="<?= htmlspecialchars(om_t('Войти','Login')) ?>"></a>
              <?php endif; ?>
            </div>
          </div>
        </div>
        <?php
    }

    function render_language_switcher() {
        $base = basename($_SERVER['PHP_SELF']);
        $qs = $_GET;
        $qs['lang'] = 'ru';
        $ruUrl = $base . '?' . http_build_query($qs);
        $qs['lang'] = 'en';
        $enUrl = $base . '?' . http_build_query($qs);
        $lang = om_lang();
        ?>
        <div class="om-lang-switch">
          <?= htmlspecialchars(om_t('Язык сайта:', 'Site language:')) ?>
          <a href="<?= htmlspecialchars($ruUrl) ?>" class="<?= $lang === 'ru' ? 'active' : '' ?>">Русский</a>
          <a href="<?= htmlspecialchars($enUrl) ?>" class="<?= $lang === 'en' ? 'active' : '' ?>">English</a>
        </div>
        <?php
    }
}
?>
