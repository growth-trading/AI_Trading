---
description: Hướng dẫn thiết kế UI/UX dark-theme — áp dụng khi làm việc với templates/ và static/
globs:
  - templates/**
  - static/**
---

## Phong cách tổng thể

Dark-theme SaaS hiện đại — tham khảo `Design.jpg`. Giao diện tối màu, typography lớn, bố cục thoáng, cảm giác cao cấp. Ưu tiên whitespace.

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
