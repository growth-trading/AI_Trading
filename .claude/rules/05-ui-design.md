---
description: UI/UX dark-theme, theme system (dark/light), i18n VI/EN, floating controls — áp dụng khi làm việc với templates/ và static/
globs:
  - templates/**
  - static/**
---

## Phong cách tổng thể

Dark-theme SaaS hiện đại — tham khảo `Design.jpg`. Giao diện tối màu, typography lớn, bố cục thoáng, cảm giác cao cấp. Ưu tiên whitespace.

## Icon Libraries

- **Bootstrap Icons 1.11** — dùng cho toàn bộ UI (navbar, buttons, badges, v.v.): class `bi bi-*`
- **Font Awesome 6.7.2** — dùng cho floating controls: class `fa-solid fa-*`
  - Moon (dark mode): `fa-solid fa-moon`
  - Sun (light mode): `fa-solid fa-sun`

## Theme System (Dark / Light)

Toàn bộ màu sắc dùng CSS custom properties trên `:root`. Light theme override bằng `[data-theme="light"]` trên `<html>`.

- **Anti-flash script** — inline trong `<head>` trước khi CSS load, đọc `localStorage('ait-theme')` và gán `data-theme` ngay lập tức, tránh flash màu sai khi reload trang.
- **Lưu trữ**: `localStorage.setItem('ait-theme', theme)` — key `ait-theme`, giá trị `'dark'` hoặc `'light'`
- **Hàm JS**: `applyTheme(theme)` trong `static/js/main.js` — cập nhật `data-theme`, localStorage, icon `#themeIcon`, label `#themeLabel`

```css
/* Dark (default) dùng :root */
/* Light override */
[data-theme="light"] { --bg-main: #F8FAFC; --bg-card: #FFFFFF; --text-main: #0F172A; ... }
[data-theme="light"] #mainNav { background: rgba(248,250,252,0.88); }
```

## i18n System (Tiếng Việt / English)

Không dùng Django i18n framework. Toàn bộ xử lý phía client.

- **Đánh dấu text** bằng attribute `data-i18n="key"` trên phần tử HTML
- **Placeholder input**: dùng `data-i18n-placeholder="key"` — `applyLang` sẽ gán `el.setAttribute('placeholder', ...)`
- **Dictionary**: `const i18n = { vi: {...}, en: {...} }` trong `static/js/main.js` — ~120+ keys, nhóm theo prefix:

| Prefix | Trang |
|--------|-------|
| `nav.*`, `footer.*` | base.html (navbar, footer) |
| `hero.*`, `stat.*`, `feat*`, `how.*`, `step*`, `cta.*` | landing page |
| `auth.login.*`, `auth.register.*`, `auth.label.*`, `auth.otp.*`, `auth.btn.*`, `auth.or`, ... | login / register / verify OTP |
| `dep.*` | trang nạp tiền |
| `prof.*` | trang hồ sơ |
| `dash.*` | dashboard |
| `com.th.*`, `com.coins_unit`, `com.no_tx` | dùng chung (table headers, đơn vị) |
| `err404.*` | trang 404 |

- **Hàm JS**: `applyLang(lang)` — query `[data-i18n]` → set `textContent`; query `[data-i18n-placeholder]` → set `placeholder`; cập nhật `data-lang` và localStorage
- **Lưu trữ**: `localStorage.setItem('ait-lang', lang)` — key `ait-lang`, giá trị `'vi'` hoặc `'en'`
- **Thêm key mới**: thêm vào cả `i18n.vi` và `i18n.en`, gán `data-i18n="key"` vào HTML
- **Button có icon**: đặt `data-i18n` trên `<span>` bọc text bên trong, không đặt lên thẻ `<button>` (vì `textContent` sẽ xóa mất icon `<i>`)

## Floating Controls (bottom-right)

Hai nút cố định góc dưới phải (`position: fixed; bottom: 28px; right: 24px`), class `.floating-controls` / `.floating-btn`.

```html
<div class="floating-controls">
  <button type="button" class="floating-btn" id="themeToggle">
    <i class="fa-solid fa-moon" id="themeIcon"></i>
    <span id="themeLabel">Dark</span>
  </button>
  <button type="button" class="floating-btn" id="langToggle">
    <span class="fab-flag" id="langFlag">🇻🇳</span>   <!-- 🇺🇸 khi EN -->
  </button>
</div>
```

**Hiệu ứng CSS**:
- Entrance: `fab-enter` animation trượt lên từ dưới khi page load
- Hover: `translateY(-5px) scale(1.07)` + accent glow `box-shadow`
- Click: ripple lan rộng từ tâm (`::before` pseudo-element)
- Theme button: shimmer sweep mỗi 4 giây (`fab-shimmer` keyframe)
- Lang button: pulse glow nhịp thở mỗi 3 giây (`fab-pulse` keyframe)

**Lưu ý quan trọng**: `<div class="floating-controls">` **phải đặt trước** `<script src="main.js">` trong base.html (xem `03-architecture.md`).

## Bảng màu

```
Nền chính:        #0D0D0D / #0F1117
Nền card/section: #1A1A2E / #16213E
Accent chính:     #3B82F6  (CTA, highlight, border active)
Accent phụ:       #6366F1  (gradient với accent chính)
Text chính:       #F1F5F9
Text phụ:         #94A3B8
Border/divider:   #1E293B
Thành công:       #10B981  (COMPLETED)
Cảnh báo/Chờ:    #F59E0B  (PENDING)
Lỗi:             #EF4444  (FAILED)
```

## Typography

- Font: `Inter` (Google Fonts)
- Hero headline: `3.5rem / weight 800`, line-height chặt
- Section headline: `2rem / weight 700`
- Body: `1rem / weight 400`, màu text phụ (`#94A3B8`)
- Badge/label: `0.75rem / weight 600`, uppercase + letter-spacing

## Components tái sử dụng

**Card**
```css
background: #1A1A2E;
border: 1px solid #1E293B;
border-radius: 12px;
padding: 24px;
transition: all 0.2s ease;
/* hover: */ transform: translateY(-4px); box-shadow: 0 8px 30px rgba(59,130,246,0.15);
```

**Button primary**
```css
background: linear-gradient(135deg, #3B82F6, #6366F1);
border-radius: 8px;
padding: 12px 28px;
```

**Button secondary**
```css
background: transparent;
border: 1px solid #3B82F6;
color: #3B82F6;
```

**Badge/Status** — pill shape, màu theo trạng thái (COMPLETED=#10B981, PENDING=#F59E0B, FAILED=#EF4444)

**Input field**
```css
background: #1E293B;
border: 1px solid #334155;
/* focus: */ border-color: #3B82F6; box-shadow: 0 0 0 3px rgba(59,130,246,0.2);
```

**Table**
```css
background: #111827;       /* table bg */
/* header: */ background: #1F2937;
/* row hover: */ background: #1E2A3A;
```

## Dashboard (sau đăng nhập)

- Sidebar trái: bg `#111827`, active item highlight `#3B82F6`
- Stat Card: số lớn + trend indicator cho coins / số giao dịch
- Bảng lịch sử: badge status, TxHash rút gọn + copy button

## Animation & Hiệu ứng

- Default transition: `transition: all 0.2s ease`
- Scroll fade-in: `IntersectionObserver` + CSS class `animate-fadeInUp`
- Loading state: skeleton screen (không dùng spinner đơn thuần)
- Số liệu tăng: count-up animation khi vào viewport

## Responsive

Mobile-first, breakpoints: `sm:640px  md:768px  lg:1024px  xl:1280px`

- Navbar mobile: hamburger menu + slide-in drawer
- Features grid: 3 cột → 1 cột trên mobile
- Dashboard sidebar: collapse thành bottom nav trên mobile
