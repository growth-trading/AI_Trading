/* RichRichAITrading — Main JS */

// Navbar scroll effect
const nav = document.getElementById('mainNav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 50);
  });
}

// IntersectionObserver — fade-in on scroll, replays every time
const scrollEls = document.querySelectorAll('.animate-on-scroll');
if (scrollEls.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      const el = entry.target;
      if (entry.isIntersecting) {
        el.classList.remove('visible');
        void el.offsetWidth; // force reflow — restarts animation
        el.classList.add('visible');
      } else {
        el.classList.remove('visible');
      }
    });
  }, { threshold: 0.12 });
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
  function fallback() {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.top = '-9999px';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
    showToast(msg, 'success');
  }
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => showToast(msg, 'success')).catch(fallback);
  } else {
    fallback();
  }
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
  const msgSpan = document.createElement('span');
  msgSpan.textContent = message;
  const closeBtn = document.createElement('button');
  closeBtn.className = 'toast-close';
  closeBtn.textContent = '×';
  closeBtn.onclick = () => toast.remove();
  toast.innerHTML = `<i class="bi bi-${icon} me-2"></i>`;
  toast.appendChild(msgSpan);
  toast.appendChild(closeBtn);
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
    'hero.cta.deposit': 'Nạp tiền ngay',
    'dep.qr.hint':      'Quét mã để sao chép địa chỉ',
    'nav.ai-trading':  'AI Trading',
    'nav.deposit':     'Nạp tiền',
    'nav.coins':       'xu',
    'nav.login':       'Đăng nhập',
    'nav.signup':      'Đăng ký ngay',
    'nav.register':    'Đăng ký',
    'nav.profile':     'Hồ sơ',
    'nav.settings':    'Cài đặt',
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
    /* stats */
    'stat.vol':     'Giao dịch xử lý',
    'stat.success': 'Tỉ lệ thành công',
    'stat.users':   'Người dùng tin dùng',
    'stat.uptime':  'Hoạt động liên tục',
    /* features */
    'feat.badge':    'Tính năng',
    'feat.title':    'Tại sao chọn RichAITrading?',
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
    'cta.subtitle': 'Tham gia cùng 500+ traders đang tin dùng RichAITrading để tối ưu lợi nhuận mỗi ngày.',
    'cta.btn1':     'Đăng ký ngay',
    'cta.btn2':     'Tìm hiểu thêm',
    /* auth — login */
    'auth.login.title':   'Chào mừng trở lại',
    'auth.login.sub':     'Đăng nhập để sử dụng tất cả các dịch vụ của RichAITrading',
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
    'auth.label.username':        'Tên đăng nhập',
    'auth.label.password':        'Mật khẩu',
    'auth.label.referral':        'Mã giới thiệu',
    'auth.label.referral_optional': '(không bắt buộc)',
    'auth.label.confirm_pw': 'Xác nhận mật khẩu',
    'auth.label.country':    'Quốc gia',
    /* auth — OTP */
    'auth.otp.title':   'Xác thực Email',
    'auth.otp.sent':    'Chúng tôi đã gửi mã 6 chữ số đến',
    'auth.otp.btn':     'Xác nhận mã OTP',
    'auth.otp.no_code': 'Không nhận được mã?',
    'auth.otp.resend':  'Gửi lại',
    'auth.otp.expires': 'Mã có hiệu lực trong',
    'auth.otp.expired': 'Mã đã hết hạn. Vui lòng gửi lại.',
    /* deposit */
    'dep.title':           'Nạp tiền USDT',
    'dep.sub':             'Chuyển USDT đến ví Admin và dán TxHash để nhận xu ngay.',
    'dep.wallet.title':    'Thông tin ví nhận',
    'dep.wallet.addr':     'Địa chỉ ví Admin',
    'dep.copy':            'Sao chép',
    'dep.rate':            'Tỉ lệ:',
    'dep.guide.step1':     'Đăng nhập sàn → vào mục Rút tiền / Withdraw → chọn token USDT',
    'dep.guide.step2':     'Chọn mạng BSC (BEP-20) — bắt buộc, không dùng ERC-20 hay TRC-20',
    'dep.guide.step3':     'Dán địa chỉ ví Admin (sao chép từ bên trái) vào ô địa chỉ nhận',
    'dep.guide.step4':     'Nhập số lượng USDT → xác nhận rút tiền',
    'dep.guide.step5':     'Chờ blockchain xác nhận giao dịch (1–5 phút)',
    'dep.guide.step6':     'Vào Lịch sử rút tiền → tìm giao dịch → copy TxHash',
    'dep.guide.step7':     'Nhấn nút bên dưới để xác minh và nhận xu ngay lập tức',
    'dep.guide.network.title': 'Chọn sai mạng = mất tiền',
    'dep.guide.network.desc':  'Chỉ chuyển qua mạng BSC (BEP-20). Gửi qua ERC-20 (Ethereum) hoặc TRC-20 (Tron) sẽ không được ghi nhận và không thể hoàn tiền.',
    'dep.method.select':        'Chọn phương thức nạp tiền',
    'dep.method.select.sub':    'Chọn cách bạn muốn gửi USDT',
    'dep.method.exchange':      'Sàn giao dịch',
    'dep.method.exchange.desc': 'Binance, OKX, Bybit và các sàn khác',
    'dep.method.metamask':      'MetaMask',
    'dep.method.metamask.desc': 'Ví Web3 phi tập trung',
    'dep.back':                 'Quay lại',
    'dep.mm.steps.title':       'Hướng dẫn gửi từ MetaMask',
    'dep.mm.step1':             'Mở MetaMask, chuyển sang mạng BSC (BNB Smart Chain)',
    'dep.mm.step2':             'Chọn token USDT — điền địa chỉ ví Admin và số lượng',
    'dep.mm.step3':             'Xác nhận và chờ giao dịch hoàn tất (1–5 phút)',
    'dep.mm.step4':             'Vào Activity → Chi tiết giao dịch → copy TxHash',
    'dep.mm.step5':             'Nhấn nút bên dưới để xác minh và nhận xu ngay lập tức',
    'dep.verify.open':          'Xác minh nạp tiền',
    'dep.modal.title':          'Xác minh giao dịch',
    'dep.modal.desc':           'Dán Transaction Hash của giao dịch vừa gửi để xác minh và nhận xu ngay lập tức.',
    'dep.tx.title':        'Hướng dẫn gửi từ sàn',
    'dep.step1':           'Chuyển USDT đến ví Admin',
    'dep.step2':           'Sao chép Transaction Hash',
    'dep.step3':           'Dán TxHash vào bên dưới',
    'dep.tx.help':         'MetaMask: Activity → Chi tiết giao dịch  |  Sàn: Lịch sử rút tiền → TxHash',
    'dep.btn.verify':      'Xác minh & Nạp tiền',
    'dep.security.title':  'Bảo mật tuyệt đối',
    'dep.security.desc':   'Hệ thống kiểm tra TxHash trực tiếp qua BSC. Mỗi TxHash chỉ được xử lý một lần.',
    'dep.history':         'Lịch sử nạp tiền',
    'dep.empty':           'Chưa có giao dịch nào. Thực hiện nạp tiền đầu tiên của bạn!',
    /* profile */
    'prof.title':       'Hồ sơ cá nhân',
    'prof.stat.txs':    'Giao dịch',
    'prof.edit.title':  'Thông tin cá nhân',
    'prof.label.last':    'Họ',
    'prof.label.first':   'Tên',
    'prof.label.email':   'Email',
    'prof.label.phone':       'Số điện thoại',
    'prof.label.address':     'Địa chỉ',
    'prof.label.bsc_wallet':  'Ví BSC nhận hoa hồng',
    'prof.payout.no_wallet_pre':  'Vui lòng cập nhật',
    'prof.payout.no_wallet_post': 'trong phần Thông tin cá nhân trước.',
    'prof.label.country': 'Quốc gia',
    'prof.btn.edit':      'Chỉnh sửa',
    'prof.btn.save':      'Lưu thay đổi',
    'prof.btn.cancel':    'Hủy',
    /* referral */
    'prof.referral.title':          'Chương trình giới thiệu',
    'prof.referral.your_code':      'Mã giới thiệu của bạn',
    'prof.referral.hint':           'Chia sẻ mã này để nhận hoa hồng khi bạn bè nạp xu.',
    'prof.referral.count':          'Số người đã giới thiệu:',
    'prof.referral.referred_by':    'Được giới thiệu bởi:',
    'prof.referral.stat.people':    'Người đã giới thiệu',
    'prof.referral.stat.direct':    'trực tiếp',
    'prof.referral.stat.indirect':  'cấp 2',
    'prof.referral.stat.earned':    'Hoa hồng tích lũy',
    'prof.referral.rate_label':     'Hoa hồng:',
    'prof.payout.title':            'Rút hoa hồng về ví',
    'prof.payout.open':             'Đang mở thanh toán',
    'prof.payout.closed':           'Mở vào 2 ngày cuối tháng',
    'prof.payout.min_label':        'Tối thiểu:',
    'prof.payout.no_wallet':        'Vui lòng cập nhật Ví BSC nhận hoa hồng trong phần Thông tin cá nhân trước.',
    'prof.payout.wallet_label':     'Ví nhận:',
    'prof.payout.btn':              'Rút hoa hồng ngay',
    'prof.payout.not_enough':       'Chưa đủ xu tối thiểu.',
    'prof.payout.history':          'Lịch sử rút hoa hồng',
    'prof.payout.status.completed': 'Hoàn tất',
    'prof.payout.status.pending':   'Đang xử lý',
    'prof.payout.status.failed':    'Thất bại',
    'prof.referral.earned_title':    'Xu hoa hồng tích lũy',
    'prof.referral.earned_hint':     'Tổng xu nhận được từ hoa hồng giới thiệu (F1: 40%, F2: 20% giá trị gói bạn bè mua).',
    /* trading page */
    'trad.hero.title':    'Công nghệ giao dịch thế hệ mới',
    'trad.hero.sub':      'Thuật toán AI phân tích thị trường 24/7, tự động hóa chiến lược và tối ưu lợi nhuận.',
    'trad.algo.badge':    'Thuật toán',
    'trad.algo.title':    'Trí tuệ nhân tạo phân tích thị trường',
    'trad.algo.desc':     'Mô hình học máy được huấn luyện trên hàng triệu điểm dữ liệu lịch sử, liên tục cập nhật để thích nghi với điều kiện thị trường thay đổi.',
    'trad.algo.f1.title': 'Phân tích đa khung thời gian',
    'trad.algo.f1.desc':  'Kết hợp tín hiệu từ M15, H1, H4, D1 để lọc nhiễu và xác nhận xu hướng.',
    'trad.algo.f2.title': '50+ chỉ báo kỹ thuật',
    'trad.algo.f2.desc':  'RSI, MACD, Bollinger Bands, Ichimoku, ATR và nhiều chỉ báo tùy chỉnh.',
    'trad.algo.f3.title': 'Phản ứng tức thì',
    'trad.algo.f3.desc':  'Đặt lệnh trong vòng mili-giây khi phát hiện cơ hội, không bỏ lỡ điểm vào lệnh tốt.',
    'trad.algo.stat.month': 'Tháng này',
    'trad.bt.badge':  'Backtest',
    'trad.bt.title':  'Kết quả kiểm chứng lịch sử',
    'trad.bt.sub':    'Chiến lược đã được kiểm thử trên dữ liệu 5 năm trước khi triển khai thực tế.',
    'trad.bt.profit': 'Lợi nhuận',
    'trad.bt.period': 'Kỳ test',
    'trad.bt.years':  '5 năm',
    'trad.cta.title':    'Sẵn sàng bắt đầu?',
    'trad.cta.sub':      'Nạp USDT và kích hoạt bot giao dịch của bạn ngay hôm nay.',
    'trad.cta.deposit':  'Nạp tiền ngay',
    'trad.cta.register': 'Đăng ký miễn phí',
    'trad.ai.btn':          'AI Phân tích',
    'trad.ai.loading':      'Đang phân tích...',
    'trad.ai.loading_sub':  'AI đang đọc và phân tích dữ liệu thực tế',
    'trad.ai.result_title': 'Kết quả phân tích AI',
    'trad.ai.entry':        'Vào lệnh',
    'trad.ai.history':      'Lịch sử phân tích',
    'trad.ai.history_empty':'Chưa có phân tích nào',
    'trad.ai.back_history': 'Lịch sử',
    'trad.ai.disclaimer':   '⚠️ Tín hiệu chỉ mang tính tham khảo, không phải khuyến nghị đầu tư. Giao dịch luôn có rủi ro.',
    'trad.ind.label':       'Chỉ báo',
    'trad.ind.group.ma':    'Đường trung bình',
    'trad.ind.group.bb':    'Dải Bollinger',
    'trad.ind.group.osc':   'Dao động',
    'trad.sym.placeholder': 'VD: NASDAQ:NVDA',
    'trad.chart.realtime':  'Dữ liệu thời gian thực từ TradingView',
    /* subscription plans */
    'trad.sub.badge':        'AI Trading Bot',
    'trad.sub.title':        'Mở khóa AI Trading Bot',
    'trad.sub.sub':          'Phân tích chart không giới hạn với AI + TAAPI.io',
    'trad.sub.plan.week':    'Tuần',
    'trad.sub.plan.month':   'Tháng',
    'trad.sub.plan.year':    'Năm',
    'trad.sub.days':         'ngày',
    'trad.sub.buy':          'Mua ngay',
    'trad.sub.popular':      'Phổ biến nhất',
    'trad.sub.saving':       'Tiết kiệm 33%',
    'trad.sub.f.unlimited':  'Phân tích không giới hạn',
    'trad.sub.f.realtime':   'Dữ liệu thời gian thực',
    'trad.sub.f.gemini':     'AI Vision',
    'trad.sub.f.priority':   'Ưu tiên xử lý',
    'trad.sub.balance':      'Số dư của bạn:',
    'trad.sub.topup':        'Nạp thêm xu',
    'trad.sub.active':       'AI Trading Đang Hoạt Động',
    'trad.sub.expires':      'Hết hạn:',
    'trad.sub.renew':        'Gia hạn',
    'trad.sub.renew_title':  'Gia hạn AI Trading',
    'trad.sub.renew_note':   'Gia hạn từ ngày hết hạn hiện tại',
    /* tradingview */
    'tv.subtitle':        'Chọn layout phân tích phù hợp — xem chart real-time với đầy đủ indicator của chuyên gia.',
    'tv.status.active':   'Đang hoạt động',
    'tv.status.inactive': 'Chưa đăng ký',
    'tv.feat.realtime':   'Chart real-time chuyên gia',
    'tv.feat.indicators': 'MACD · RSI · EMA · Supertrend',
    'tv.feat.levels':     'Vùng hỗ trợ / kháng cự',
    'tv.expiry':          'Hết hạn:',
    'tv.btn.view':        'Xem chart',
    'tv.btn.buy':         'Mua ngay',
    'tv.price.from':      'Từ',
    'tv.price.week':      'xu / tuần',
    'tv.empty':           'Chưa có sản phẩm nào.',
    'tv.modal.title':     'Mua gói TradingView',
    'tv.plan.week':       'Tuần',
    'tv.plan.month':      'Tháng',
    'tv.plan.year':       'Năm',
    'tv.plan.days7':      '7 ngày',
    'tv.plan.days30':     '30 ngày',
    'tv.plan.days365':    '365 ngày',
    'tv.plan.popular':    'Phổ biến',
    'tv.modal.coins':     'Số dư:',
    'tv.modal.topup':     'Nạp thêm',
    'tv.modal.select':    'Chọn gói để tiếp tục',
    'tv.modal.buy_week':  'Mua gói Tuần',
    'tv.modal.buy_month': 'Mua gói Tháng',
    'tv.modal.buy_year':  'Mua gói Năm',
    'tv.modal.processing':'Đang xử lý...',
    'tv.modal.retry':     'Thử lại',
    'tv.modal.err':       'Mua gói thất bại.',
    'tv.modal.err_conn':  'Lỗi kết nối. Vui lòng thử lại.',
    /* settings */
    'settings.title':                  'Cài đặt',
    'settings.appearance.title':       'Giao diện',
    'settings.appearance.desc':        'Chọn chủ đề hiển thị cho ứng dụng.',
    'settings.appearance.dark':        'Tối',
    'settings.appearance.dark_desc':   'Nền tối, dễ nhìn ban đêm',
    'settings.appearance.light':       'Sáng',
    'settings.appearance.light_desc':  'Nền sáng, phù hợp ban ngày',
    'settings.lang.title':             'Ngôn ngữ',
    'settings.lang.desc':              'Chọn ngôn ngữ hiển thị cho toàn bộ ứng dụng.',
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
    'hero.cta.deposit': 'Deposit Now',
    'dep.qr.hint':      'Scan to copy address',
    'nav.ai-trading':  'AI Trading',
    'nav.deposit':     'Deposit',
    'nav.coins':       'coins',
    'nav.login':       'Login',
    'nav.signup':      'Get Started',
    'nav.register':    'Register',
    'nav.profile':     'Profile',
    'nav.settings':    'Settings',
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
    /* stats */
    'stat.vol':     'Trading Volume',
    'stat.success': 'Success Rate',
    'stat.users':   'Trusted Users',
    'stat.uptime':  'Always Online',
    /* features */
    'feat.badge':    'Features',
    'feat.title':    'Why Choose RichAITrading?',
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
    'cta.subtitle': 'Join 500+ traders who trust RichAITrading to maximize their daily profits.',
    'cta.btn1':     'Sign Up Now',
    'cta.btn2':     'Learn More',
    /* auth — login */
    'auth.login.title':   'Welcome Back',
    'auth.login.sub':     'Sign in to use all RichAITrading services',
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
    'auth.label.username':        'Username',
    'auth.label.password':        'Password',
    'auth.label.referral':        'Referral Code',
    'auth.label.referral_optional': '(optional)',
    'auth.label.confirm_pw': 'Confirm Password',
    'auth.label.country':    'Country',
    /* auth — OTP */
    'auth.otp.title':   'Email Verification',
    'auth.otp.sent':    'We sent a 6-digit code to',
    'auth.otp.btn':     'Verify OTP Code',
    'auth.otp.no_code': "Didn't receive the code?",
    'auth.otp.resend':  'Resend',
    'auth.otp.expires': 'Code valid for',
    'auth.otp.expired': 'Code expired. Please resend.',
    /* deposit */
    'dep.title':           'Deposit USDT',
    'dep.sub':             'Transfer USDT to Admin wallet and paste TxHash to receive coins instantly.',
    'dep.wallet.title':    'Receiving Wallet',
    'dep.wallet.addr':     'Admin Wallet Address',
    'dep.copy':            'Copy',
    'dep.rate':            'Rate:',
    'dep.guide.step1':     'Log in to exchange → go to Withdraw → select USDT token',
    'dep.guide.step2':     'Select network BSC (BEP-20) — required, do NOT use ERC-20 or TRC-20',
    'dep.guide.step3':     'Paste Admin wallet address (copied from the left) into the recipient field',
    'dep.guide.step4':     'Enter USDT amount → confirm withdrawal',
    'dep.guide.step5':     'Wait for blockchain confirmation (1–5 minutes)',
    'dep.guide.step6':     'Go to Withdrawal History → find the transaction → copy TxHash',
    'dep.guide.step7':     'Click the button below to verify and receive coins instantly',
    'dep.guide.network.title': 'Wrong network = lost funds',
    'dep.guide.network.desc':  'Only send via BSC (BEP-20). Sending via ERC-20 (Ethereum) or TRC-20 (Tron) will not be recognized and cannot be refunded.',
    'dep.method.select':        'Select Deposit Method',
    'dep.method.select.sub':    'Choose how you want to send USDT',
    'dep.method.exchange':      'Exchange',
    'dep.method.exchange.desc': 'Binance, OKX, Bybit and more',
    'dep.method.metamask':      'MetaMask',
    'dep.method.metamask.desc': 'Decentralized Web3 wallet',
    'dep.back':                 'Go Back',
    'dep.mm.steps.title':       'How to Send from MetaMask',
    'dep.mm.step1':             'Open MetaMask, switch to BSC (BNB Smart Chain) network',
    'dep.mm.step2':             'Select USDT token — enter Admin wallet address and amount',
    'dep.mm.step3':             'Confirm and wait for transaction to complete (1–5 min)',
    'dep.mm.step4':             'Go to Activity → Transaction Details → copy TxHash',
    'dep.mm.step5':             'Click the button below to verify and receive coins instantly',
    'dep.verify.open':          'Verify Deposit',
    'dep.modal.title':          'Verify Transaction',
    'dep.modal.desc':           'Paste the Transaction Hash from your recent transfer to verify and receive coins instantly.',
    'dep.tx.title':        'Exchange Guide',
    'dep.step1':           'Transfer USDT to Admin Wallet',
    'dep.step2':           'Copy Transaction Hash',
    'dep.step3':           'Paste TxHash below',
    'dep.tx.help':         'MetaMask: Activity → Transaction Details  |  Exchange: Withdrawal History → TxHash',
    'dep.btn.verify':      'Verify & Deposit',
    'dep.security.title':  'Absolute Security',
    'dep.security.desc':   'System verifies TxHash directly via BSC. Each TxHash is processed only once.',
    'dep.history':         'Deposit History',
    'dep.empty':           'No transactions yet. Make your first deposit!',
    /* profile */
    'prof.title':       'Personal Profile',
    'prof.stat.txs':    'Transactions',
    'prof.edit.title':  'Personal Information',
    'prof.label.last':    'Last Name',
    'prof.label.first':   'First Name',
    'prof.label.email':   'Email',
    'prof.label.phone':       'Phone Number',
    'prof.label.address':     'Address',
    'prof.label.bsc_wallet':  'BSC Wallet for Commission',
    'prof.payout.no_wallet_pre':  'Please update your',
    'prof.payout.no_wallet_post': 'in Personal Information first.',
    'prof.label.country': 'Country',
    'prof.btn.edit':      'Edit',
    'prof.btn.save':      'Save Changes',
    'prof.btn.cancel':    'Cancel',
    /* referral */
    'prof.referral.title':          'Referral Program',
    'prof.referral.your_code':      'Your Referral Code',
    'prof.referral.hint':           'Share this code to earn commissions when friends deposit coins.',
    'prof.referral.count':          'Total referrals:',
    'prof.referral.referred_by':    'Referred by:',
    'prof.referral.stat.people':    'People Referred',
    'prof.referral.stat.direct':    'direct',
    'prof.referral.stat.indirect':  'level 2',
    'prof.referral.stat.earned':    'Accumulated Commission',
    'prof.referral.rate_label':     'Commission:',
    'prof.payout.title':            'Withdraw Commission',
    'prof.payout.open':             'Withdrawal Open',
    'prof.payout.closed':           'Opens last 2 days of month',
    'prof.payout.min_label':        'Minimum:',
    'prof.payout.no_wallet':        'Please update your BSC Wallet in Personal Information first.',
    'prof.payout.wallet_label':     'Recipient wallet:',
    'prof.payout.btn':              'Withdraw Now',
    'prof.payout.not_enough':       'Not enough coins to withdraw.',
    'prof.payout.history':          'Withdrawal History',
    'prof.payout.status.completed': 'Completed',
    'prof.payout.status.pending':   'Pending',
    'prof.payout.status.failed':    'Failed',
    'prof.referral.earned_title':    'Accumulated Commission Coins',
    'prof.referral.earned_hint':     'Total coins earned from referral commissions (F1: 40%, F2: 20% of friends\' plan value).',
    /* trading page */
    'trad.hero.title':    'Next-Generation Trading Technology',
    'trad.hero.sub':      'AI algorithms analyze markets 24/7, automate strategies and maximize profits.',
    'trad.algo.badge':    'Algorithm',
    'trad.algo.title':    'Artificial Intelligence Market Analysis',
    'trad.algo.desc':     'Machine learning models trained on millions of historical data points, continuously updated to adapt to changing market conditions.',
    'trad.algo.f1.title': 'Multi-Timeframe Analysis',
    'trad.algo.f1.desc':  'Combines signals from M15, H1, H4, D1 to filter noise and confirm trends.',
    'trad.algo.f2.title': '50+ Technical Indicators',
    'trad.algo.f2.desc':  'RSI, MACD, Bollinger Bands, Ichimoku, ATR and many custom indicators.',
    'trad.algo.f3.title': 'Instant Response',
    'trad.algo.f3.desc':  'Places orders within milliseconds when an opportunity is detected — never miss a good entry.',
    'trad.algo.stat.month': 'This Month',
    'trad.bt.badge':  'Backtest',
    'trad.bt.title':  'Historical Performance Results',
    'trad.bt.sub':    'Strategies tested on 5 years of historical data before live deployment.',
    'trad.bt.profit': 'Profit',
    'trad.bt.period': 'Test Period',
    'trad.bt.years':  '5 years',
    'trad.cta.title':    'Ready to Start?',
    'trad.cta.sub':      'Deposit USDT and activate your trading bot today.',
    'trad.cta.deposit':  'Deposit Now',
    'trad.cta.register': 'Register Free',
    'trad.ai.btn':          'AI Analyze',
    'trad.ai.loading':      'Analyzing...',
    'trad.ai.loading_sub':  'AI is reading and analyzing real market data',
    'trad.ai.result_title': 'AI Analysis Result',
    'trad.ai.entry':        'Entry',
    'trad.ai.history':      'Analysis History',
    'trad.ai.history_empty':'No analyses yet',
    'trad.ai.back_history': 'History',
    'trad.ai.disclaimer':   '⚠️ Signals are for reference only, not investment advice. Trading always involves risk.',
    'trad.ind.label':       'Indicators',
    'trad.ind.group.ma':    'Moving Average',
    'trad.ind.group.bb':    'Bollinger Bands',
    'trad.ind.group.osc':   'Oscillators',
    'trad.sym.placeholder': 'e.g. NASDAQ:NVDA',
    'trad.chart.realtime':  'Real-time data from TradingView',
    /* subscription plans */
    'trad.sub.badge':        'AI Trading Bot',
    'trad.sub.title':        'Unlock AI Trading Bot',
    'trad.sub.sub':          'Unlimited chart analysis with AI + TAAPI.io',
    'trad.sub.plan.week':    'Weekly',
    'trad.sub.plan.month':   'Monthly',
    'trad.sub.plan.year':    'Yearly',
    'trad.sub.days':         'days',
    'trad.sub.buy':          'Buy Now',
    'trad.sub.popular':      'Most Popular',
    'trad.sub.saving':       'Save 33%',
    'trad.sub.f.unlimited':  'Unlimited analysis',
    'trad.sub.f.realtime':   'Real-time data',
    'trad.sub.f.gemini':     'AI Vision',
    'trad.sub.f.priority':   'Priority processing',
    'trad.sub.balance':      'Your balance:',
    'trad.sub.topup':        'Top up coins',
    'trad.sub.active':       'AI Trading Active',
    'trad.sub.expires':      'Expires:',
    'trad.sub.renew':        'Renew',
    'trad.sub.renew_title':  'Renew AI Trading',
    'trad.sub.renew_note':   'Extended from current expiry date',
    /* tradingview */
    'tv.subtitle':        'Choose your analysis layout — view real-time charts with expert-grade indicators.',
    'tv.status.active':   'Active',
    'tv.status.inactive': 'Not subscribed',
    'tv.feat.realtime':   'Expert real-time chart',
    'tv.feat.indicators': 'MACD · RSI · EMA · Supertrend',
    'tv.feat.levels':     'Support / resistance zones',
    'tv.expiry':          'Expires:',
    'tv.btn.view':        'View chart',
    'tv.btn.buy':         'Buy now',
    'tv.price.from':      'From',
    'tv.price.week':      'coins / week',
    'tv.empty':           'No products available.',
    'tv.modal.title':     'Buy TradingView Package',
    'tv.plan.week':       'Weekly',
    'tv.plan.month':      'Monthly',
    'tv.plan.year':       'Yearly',
    'tv.plan.days7':      '7 days',
    'tv.plan.days30':     '30 days',
    'tv.plan.days365':    '365 days',
    'tv.plan.popular':    'Popular',
    'tv.modal.coins':     'Balance:',
    'tv.modal.topup':     'Top up',
    'tv.modal.select':    'Select a plan to continue',
    'tv.modal.buy_week':  'Buy Weekly Plan',
    'tv.modal.buy_month': 'Buy Monthly Plan',
    'tv.modal.buy_year':  'Buy Yearly Plan',
    'tv.modal.processing':'Processing...',
    'tv.modal.retry':     'Retry',
    'tv.modal.err':       'Purchase failed.',
    'tv.modal.err_conn':  'Connection error. Please try again.',
    /* settings */
    'settings.title':                  'Settings',
    'settings.appearance.title':       'Appearance',
    'settings.appearance.desc':        'Choose the display theme for the application.',
    'settings.appearance.dark':        'Dark',
    'settings.appearance.dark_desc':   'Dark background, easy on the eyes at night',
    'settings.appearance.light':       'Light',
    'settings.appearance.light_desc':  'Light background, suitable for daytime',
    'settings.lang.title':             'Language',
    'settings.lang.desc':              'Choose the display language for the entire application.',
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
window.i18n = i18n;

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

}

// Apply theme
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ait-theme', theme);
}

// Init on page load (theme already set by anti-flash script; sync icon + text)
(function () {
  const theme = localStorage.getItem('ait-theme') || 'dark';
  const lang  = localStorage.getItem('ait-lang')  || 'vi';
  applyTheme(theme);
  applyLang(lang);
})();

// Re-apply when browser restores page from bfcache (back/forward navigation)
window.addEventListener('pageshow', function (e) {
  if (e.persisted) {
    applyTheme(localStorage.getItem('ait-theme') || 'dark');
    applyLang(localStorage.getItem('ait-lang') || 'vi');
  }
});

// Sidebar toggle
(function () {
  const toggle = document.getElementById('sidebarToggle');
  if (!toggle) return;
  const sidebar = document.querySelector('.sidebar');
  if (localStorage.getItem('ait-sidebar') === 'collapsed') {
    sidebar.classList.add('collapsed');
  }
  toggle.addEventListener('click', function () {
    sidebar.classList.toggle('collapsed');
    localStorage.setItem('ait-sidebar', sidebar.classList.contains('collapsed') ? 'collapsed' : 'expanded');
  });
})();
