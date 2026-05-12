/* AITrading — Main JS */

// Navbar scroll effect
const nav = document.getElementById('mainNav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 50);
  });
}

// IntersectionObserver — fade-in on scroll
const scrollEls = document.querySelectorAll('.animate-on-scroll');
if (scrollEls.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 100);
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  scrollEls.forEach(el => obs.observe(el));
}

// Count-up animation for stats
function countUp(el, target, prefix, suffix, duration) {
  const isFloat = !Number.isInteger(target);
  const start = performance.now();
  const update = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = eased * target;
    el.textContent = prefix + (isFloat ? current.toFixed(1) : Math.floor(current).toLocaleString()) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

const statItems = document.querySelectorAll('.stat-item[data-count]');
if (statItems.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target.querySelector('.stat-number');
        const target = parseFloat(entry.target.dataset.count);
        const prefix = entry.target.dataset.prefix || '';
        const suffix = entry.target.dataset.suffix || '';
        countUp(el, target, prefix, suffix, 1800);
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  statItems.forEach(el => obs.observe(el));
}

// Copy to clipboard
function copyText(text) {
  const lang = document.documentElement.getAttribute('data-lang') || 'vi';
  const msg = (i18n[lang] || i18n.vi)['copied'] || 'Copied!';
  navigator.clipboard.writeText(text).then(() => {
    showToast(msg, 'success');
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast(msg, 'success');
  });
}

// Toast notification
function showToast(message, type = 'success') {
  let container = document.querySelector('.messages-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'messages-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `alert-toast alert-toast-${type}`;
  const icon = type === 'success' ? 'check-circle-fill' : 'x-circle-fill';
  toast.innerHTML = `<i class="bi bi-${icon} me-2"></i>${message}
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// Auto-dismiss existing toasts
document.querySelectorAll('.alert-toast').forEach(el => {
  setTimeout(() => el.remove(), 5000);
});

/* =============================================
   THEME & LANGUAGE SYSTEM
   ============================================= */

const i18n = {
  vi: {
    /* navbar */
    'nav.home':        'Trang chủ',
    'nav.ai-trading':  'AI Trading',
    'nav.deposit':     'Nạp tiền',
    'nav.coins':       'xu',
    'nav.login':       'Đăng nhập',
    'nav.signup':      'Đăng ký ngay',
    'nav.register':    'Đăng ký',
    'nav.dashboard':   'Dashboard',
    'nav.profile':     'Hồ sơ',
    'nav.logout':      'Đăng xuất',
    /* footer */
    'footer.desc':     'Nền tảng giao dịch thông minh tích hợp AI — tối ưu lợi nhuận, giảm thiểu rủi ro.',
    'footer.products': 'Sản phẩm',
    'footer.account':  'Tài khoản',
    'footer.contact':  'Liên hệ',
    'footer.tagline':  'Giao dịch luôn có rủi ro. Đầu tư có trách nhiệm.',
    /* hero */
    'hero.badge':          'Nền tảng AI Trading hàng đầu Việt Nam',
    'hero.title1':         'Tối ưu lợi nhuận với',
    'hero.subtitle':       'Thuật toán AI tiên tiến phân tích thị trường 24/7. Backtest chiến lược tự động. Nạp USDT — kích hoạt bot — hưởng lợi nhuận ổn định.',
    'hero.cta1':           'Đăng ký ngay',
    'hero.cta2':           'Xem Demo',
    'hero.mockup.coins':   'Số dư xu',
    'hero.mockup.profit':  'Lợi nhuận tháng',
    'hero.mockup.bots':    'Bot đang chạy',
    /* stats */
    'stat.vol':     'Giao dịch xử lý',
    'stat.success': 'Tỉ lệ thành công',
    'stat.users':   'Người dùng tin dùng',
    'stat.uptime':  'Hoạt động liên tục',
    /* features */
    'feat.badge':    'Tính năng',
    'feat.title':    'Tại sao chọn AITrading?',
    'feat.subtitle': 'Công nghệ AI tối tân kết hợp với chiến lược giao dịch đã được kiểm chứng',
    'feat.popular':  'Phổ biến nhất',
    'feat1.title': 'Thuật toán AI tiên tiến',
    'feat1.desc':  'Mô hình học máy phân tích hàng nghìn tín hiệu thị trường theo thời gian thực. Tự động nhận dạng xu hướng XAUUSD, Forex, Crypto.',
    'feat1.li1':   'Phân tích 50+ chỉ báo kỹ thuật',
    'feat1.li2':   'Dự báo xu hướng 15 phút — 4 giờ',
    'feat1.li3':   'Cập nhật mô hình mỗi tuần',
    'feat2.title': 'Backtest tự động',
    'feat2.desc':  'Kiểm thử chiến lược với dữ liệu lịch sử 5 năm trước khi triển khai thực tế. Báo cáo Sharpe Ratio, Drawdown, Win Rate chi tiết.',
    'feat2.li1':   'Dữ liệu lịch sử 5 năm',
    'feat2.li2':   'Báo cáo PDF tự động',
    'feat2.li3':   'So sánh đa chiến lược',
    'feat3.title': 'Commission Farming',
    'feat3.desc':  'Tối ưu hóa Rebate (Back Com) khi chạy bot khối lượng lớn trên Exness & GTC. Hệ thống tự động tính toán và báo cáo hoa hồng theo ngày.',
    'feat3.li1':   'Kết nối Exness / GTC',
    'feat3.li2':   'Tối ưu rebate tự động',
    'feat3.li3':   'Báo cáo hoa hồng hàng ngày',
    /* how it works */
    'how.badge': 'Quy trình',
    'how.title': 'Bắt đầu trong 3 bước đơn giản',
    'step1.title': 'Tạo tài khoản',
    'step1.desc':  'Đăng ký miễn phí, xác thực email OTP, kích hoạt ngay lập tức.',
    'step2.title': 'Nạp USDT',
    'step2.desc':  'Chuyển USDT từ MetaMask đến ví Admin. Hệ thống tự động xác nhận và cộng xu.',
    'step3.title': 'Kích hoạt Bot',
    'step3.desc':  'Chọn chiến lược, kết nối tài khoản Exness/GTC, bot tự động giao dịch 24/7.',
    /* cta */
    'cta.title':    'Bắt đầu giao dịch thông minh hôm nay',
    'cta.subtitle': 'Tham gia cùng 500+ traders đang tin dùng AITrading để tối ưu lợi nhuận mỗi ngày.',
    'cta.btn1':     'Đăng ký ngay',
    'cta.btn2':     'Tìm hiểu thêm',
    /* auth — login */
    'auth.login.title':   'Chào mừng trở lại',
    'auth.login.sub':     'Đăng nhập để sử dụng tất cả các dịch vụ của AITrading',
    'auth.btn.login':     'Đăng nhập',
    'auth.or':            'hoặc',
    'auth.no_account':    'Chưa có tài khoản?',
    'auth.signup_free':   'Đăng ký miễn phí',
    /* auth — register */
    'auth.register.title': 'Tạo tài khoản miễn phí',
    'auth.register.sub':   'Bắt đầu giao dịch thông minh ngay hôm nay.',
    'auth.btn.create':     'Tạo tài khoản',
    'auth.has_account':    'Đã có tài khoản?',
    /* auth — shared labels */
    'auth.label.username':   'Tên đăng nhập',
    'auth.label.password':   'Mật khẩu',
    'auth.label.confirm_pw': 'Xác nhận mật khẩu',
    /* auth — OTP */
    'auth.otp.title':   'Xác thực Email',
    'auth.otp.sent':    'Chúng tôi đã gửi mã 6 chữ số đến',
    'auth.otp.btn':     'Xác nhận mã OTP',
    'auth.otp.no_code': 'Không nhận được mã?',
    'auth.otp.resend':  'Gửi lại',
    'auth.otp.expires': 'Mã có hiệu lực trong',
    'auth.otp.minutes': 'phút',
    /* deposit */
    'dep.title':           'Nạp tiền USDT',
    'dep.sub':             'Chuyển USDT qua MetaMask — hệ thống tự động xác nhận và cộng xu.',
    'dep.wallet.title':    'Thông tin ví nhận',
    'dep.wallet.addr':     'Địa chỉ ví Admin',
    'dep.copy':            'Sao chép',
    'dep.memo.label':      'Mã nạp tiền của bạn (Memo)',
    'dep.memo.help':       'Ghi mã này vào trường Memo/Note khi chuyển tiền để hệ thống tự động nhận diện.',
    'dep.rate':            'Tỉ lệ:',
    'dep.metamask':        'Kết nối MetaMask',
    'dep.tx.title':        'Xác nhận giao dịch',
    'dep.step1':           'Chuyển USDT đến ví Admin',
    'dep.step2':           'Sao chép Transaction Hash',
    'dep.step3':           'Dán TxHash vào bên dưới',
    'dep.tx.help':         'Tìm TxHash trong MetaMask > Activity > Chi tiết giao dịch',
    'dep.btn.verify':      'Xác minh & Nạp tiền',
    'dep.security.title':  'Bảo mật tuyệt đối',
    'dep.security.desc':   'Hệ thống kiểm tra TxHash trực tiếp qua BscScan API. Mỗi TxHash chỉ được xử lý một lần.',
    'dep.history':         'Lịch sử nạp tiền',
    'dep.empty':           'Chưa có giao dịch nào. Thực hiện nạp tiền đầu tiên của bạn!',
    /* profile */
    'prof.title':       'Hồ sơ cá nhân',
    'prof.stat.coins':  'Xu',
    'prof.stat.txs':    'Giao dịch',
    'prof.edit.title':  'Chỉnh sửa thông tin',
    'prof.label.last':  'Họ',
    'prof.label.first': 'Tên',
    'prof.label.email': 'Email',
    'prof.btn.save':    'Lưu thay đổi',
    'prof.tx.title':    'Toàn bộ giao dịch',
    /* dashboard */
    'dash.welcome':    'Chào mừng trở lại,',
    'dash.stat.coins': 'Số dư xu',
    'dash.stat.txs':   'Tổng giao dịch nạp',
    'dash.stat.email': 'Trạng thái Email',
    'dash.stat.memo':  'Mã nạp tiền của bạn',
    'dash.verified':   'Đã xác thực',
    'dash.unverified': 'Chưa xác thực',
    'dash.recent':     'Giao dịch gần đây',
    'dash.view_all':   'Xem tất cả',
    'dash.th.usdt':    'Số USDT',
    'dash.deposit_now':'Nạp tiền ngay',
    /* common */
    'com.coins_unit': 'xu',
    'com.th.coins':   'Xu nhận',
    'com.th.status':  'Trạng thái',
    'com.th.time':    'Thời gian',
    'com.th.date':    'Ngày',
    'com.no_tx':      'Chưa có giao dịch nào.',
    /* 404 page */
    'err404.warn_label': 'Cảnh báo:',
    'err404.warn_text':  'Trang bạn truy cập không tồn tại trên hệ thống.',
    'err404.title':      'Không tìm thấy trang',
    'err404.path_pre':   'Đường dẫn',
    'err404.path_suf':   'không tồn tại hoặc đã bị xóa.',
    'err404.detail1':    'URL không khớp với bất kỳ trang nào trong hệ thống',
    'err404.detail2':    'Đường dẫn có thể đã thay đổi hoặc bị xóa',
    'err404.detail3':    'Kiểm tra lại chính tả hoặc quay về trang chủ',
    'err404.btn_home':   'Về trang chủ',
    'err404.suggest':    'Trang gợi ý:',
    /* misc */
    'copied': 'Đã sao chép!',
  },
  en: {
    /* navbar */
    'nav.home':        'Home',
    'nav.ai-trading':  'AI Trading',
    'nav.deposit':     'Deposit',
    'nav.coins':       'coins',
    'nav.login':       'Login',
    'nav.signup':      'Let Register',
    'nav.register':    'Register',
    'nav.dashboard':   'Dashboard',
    'nav.profile':     'Profile',
    'nav.logout':      'Logout',
    /* footer */
    'footer.desc':     'AI-powered smart trading platform — maximize profits, minimize risks.',
    'footer.products': 'Products',
    'footer.account':  'Account',
    'footer.contact':  'Contact',
    'footer.tagline':  'Trading involves risk. Invest responsibly.',
    /* hero */
    'hero.badge':          "Vietnam's #1 AI Trading Platform",
    'hero.title1':         'Maximize your profits with',
    'hero.subtitle':       'Advanced AI algorithms analyze markets 24/7. Automated strategy backtesting. Deposit USDT — activate bot — earn steady profits.',
    'hero.cta1':           'Let Register',
    'hero.cta2':           'View Demo',
    'hero.mockup.coins':   'Coin Balance',
    'hero.mockup.profit':  'Monthly Profit',
    'hero.mockup.bots':    'Bots Running',
    /* stats */
    'stat.vol':     'Trading Volume',
    'stat.success': 'Success Rate',
    'stat.users':   'Trusted Users',
    'stat.uptime':  'Always Online',
    /* features */
    'feat.badge':    'Features',
    'feat.title':    'Why Choose AITrading?',
    'feat.subtitle': 'Cutting-edge AI technology combined with proven trading strategies',
    'feat.popular':  'Most Popular',
    'feat1.title': 'Advanced AI Algorithm',
    'feat1.desc':  'Machine learning models analyze thousands of market signals in real-time. Automatically identifies trends for XAUUSD, Forex, and Crypto.',
    'feat1.li1':   'Analyzes 50+ technical indicators',
    'feat1.li2':   'Trend forecasting: 15 min — 4 hours',
    'feat1.li3':   'Model updated weekly',
    'feat2.title': 'Automated Backtesting',
    'feat2.desc':  'Test strategies against 5 years of historical data before going live. Detailed Sharpe Ratio, Drawdown, and Win Rate reports.',
    'feat2.li1':   '5 years of historical data',
    'feat2.li2':   'Automatic PDF reports',
    'feat2.li3':   'Multi-strategy comparison',
    'feat3.title': 'Commission Farming',
    'feat3.desc':  'Optimize Rebate (Back Com) running high-volume bots on Exness & GTC. Automatically calculates and reports daily commissions.',
    'feat3.li1':   'Connect Exness / GTC',
    'feat3.li2':   'Automatic rebate optimization',
    'feat3.li3':   'Daily commission reports',
    /* how it works */
    'how.badge': 'Process',
    'how.title': 'Get Started in 3 Simple Steps',
    'step1.title': 'Create Account',
    'step1.desc':  'Register for free, verify your email via OTP, activate instantly.',
    'step2.title': 'Deposit USDT',
    'step2.desc':  'Send USDT from MetaMask to the Admin wallet. System auto-confirms and credits coins.',
    'step3.title': 'Activate Bot',
    'step3.desc':  'Choose a strategy, connect your Exness/GTC account, bot trades 24/7 automatically.',
    /* cta */
    'cta.title':    'Start Smart Trading Today',
    'cta.subtitle': 'Join 500+ traders who trust AITrading to maximize their daily profits.',
    'cta.btn1':     'Sign Up Now',
    'cta.btn2':     'Learn More',
    /* auth — login */
    'auth.login.title':   'Welcome Back',
    'auth.login.sub':     'Sign in to use all AITrading services',
    'auth.btn.login':     'Login',
    'auth.or':            'or',
    'auth.no_account':    "Don't have an account?",
    'auth.signup_free':   'Register Free',
    /* auth — register */
    'auth.register.title': 'Create Free Account',
    'auth.register.sub':   'Start smart trading today.',
    'auth.btn.create':     'Create Account',
    'auth.has_account':    'Already have an account?',
    /* auth — shared labels */
    'auth.label.username':   'Username',
    'auth.label.password':   'Password',
    'auth.label.confirm_pw': 'Confirm Password',
    /* auth — OTP */
    'auth.otp.title':   'Email Verification',
    'auth.otp.sent':    'We sent a 6-digit code to',
    'auth.otp.btn':     'Verify OTP Code',
    'auth.otp.no_code': "Didn't receive the code?",
    'auth.otp.resend':  'Resend',
    'auth.otp.expires': 'Code valid for',
    'auth.otp.minutes': 'minutes',
    /* deposit */
    'dep.title':           'Deposit USDT',
    'dep.sub':             'Transfer USDT via MetaMask — system auto-confirms and credits coins.',
    'dep.wallet.title':    'Receiving Wallet',
    'dep.wallet.addr':     'Admin Wallet Address',
    'dep.copy':            'Copy',
    'dep.memo.label':      'Your Deposit Code (Memo)',
    'dep.memo.help':       'Enter this code in the Memo/Note field when transferring so the system auto-detects it.',
    'dep.rate':            'Rate:',
    'dep.metamask':        'Connect MetaMask',
    'dep.tx.title':        'Confirm Transaction',
    'dep.step1':           'Transfer USDT to Admin Wallet',
    'dep.step2':           'Copy Transaction Hash',
    'dep.step3':           'Paste TxHash below',
    'dep.tx.help':         'Find TxHash in MetaMask > Activity > Transaction Details',
    'dep.btn.verify':      'Verify & Deposit',
    'dep.security.title':  'Absolute Security',
    'dep.security.desc':   'System verifies TxHash via BscScan API. Each TxHash is processed only once.',
    'dep.history':         'Deposit History',
    'dep.empty':           'No transactions yet. Make your first deposit!',
    /* profile */
    'prof.title':       'Personal Profile',
    'prof.stat.coins':  'Coins',
    'prof.stat.txs':    'Transactions',
    'prof.edit.title':  'Edit Information',
    'prof.label.last':  'Last Name',
    'prof.label.first': 'First Name',
    'prof.label.email': 'Email',
    'prof.btn.save':    'Save Changes',
    'prof.tx.title':    'All Transactions',
    /* dashboard */
    'dash.welcome':    'Welcome back,',
    'dash.stat.coins': 'Coin Balance',
    'dash.stat.txs':   'Total Deposits',
    'dash.stat.email': 'Email Status',
    'dash.stat.memo':  'Your Deposit Code',
    'dash.verified':   'Verified',
    'dash.unverified': 'Unverified',
    'dash.recent':     'Recent Transactions',
    'dash.view_all':   'View All',
    'dash.th.usdt':    'USDT Amount',
    'dash.deposit_now':'Deposit Now',
    /* common */
    'com.coins_unit': 'coins',
    'com.th.coins':   'Coins',
    'com.th.status':  'Status',
    'com.th.time':    'Time',
    'com.th.date':    'Date',
    'com.no_tx':      'No transactions yet.',
    /* 404 page */
    'err404.warn_label': 'Warning:',
    'err404.warn_text':  'The page you visited does not exist in the system.',
    'err404.title':      'Page Not Found',
    'err404.path_pre':   'The path',
    'err404.path_suf':   'does not exist or has been removed.',
    'err404.detail1':    'URL does not match any page in the system',
    'err404.detail2':    'The path may have changed or been deleted',
    'err404.detail3':    'Check the spelling or return to the home page',
    'err404.btn_home':   'Go Home',
    'err404.suggest':    'Suggested pages:',
    /* misc */
    'copied': 'Copied!',
  },
};

// Apply translations to all [data-i18n] elements
function applyLang(lang) {
  const dict = i18n[lang] || i18n.vi;
  document.documentElement.setAttribute('data-lang', lang);
  document.documentElement.lang = lang === 'en' ? 'en' : 'vi';
  localStorage.setItem('ait-lang', lang);

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key] !== undefined) el.textContent = dict[key];
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (dict[key] !== undefined) el.setAttribute('placeholder', dict[key]);
  });

  const flag = document.getElementById('langFlag');
  if (flag) flag.textContent = lang === 'vi' ? '🇻🇳' : '🇺🇸';
}

// Apply theme
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ait-theme', theme);
  const icon = document.getElementById('themeIcon');
  if (icon) icon.className = theme === 'dark' ? 'fa-regular fa-moon' : 'fa-regular fa-sun';
  const label = document.getElementById('themeLabel');
  if (label) label.textContent = theme === 'dark' ? 'Dark' : 'Light';
}

// Wire up buttons
document.getElementById('themeToggle')?.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  applyTheme(current === 'dark' ? 'light' : 'dark');
});

document.getElementById('langToggle')?.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-lang') || 'vi';
  applyLang(current === 'vi' ? 'en' : 'vi');
});

// Init on page load (theme already set by anti-flash script; sync icon + text)
(function () {
  const theme = localStorage.getItem('ait-theme') || 'dark';
  const lang  = localStorage.getItem('ait-lang')  || 'vi';
  applyTheme(theme);
  applyLang(lang);
})();
