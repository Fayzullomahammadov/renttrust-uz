# RentTrust UZ — Qo'lda Bajarilishi Kerak Bo'lgan Ishlar (TODO_MANUAL.md)

Ushbu hujjat RentTrust UZ platformasini to'liq qonuniy, barqaror va xavfsiz tijoriy ekspluatatsiyaga tushirish uchun inson aralashuvi, shartnomalar, litsenziyalar yoki moliyaviy xarajatlarni talab qiladigan vazifalarni o'z ichiga oladi.

---

## 1. Yuridik Ekspertiza va Ommaviy Oferta (Legal Review)
*O'zbekiston Respublikasi advokati yoki litsenziyalangan yuridik kompaniyasi ko'rigidan o'tkazilishi lozim.*

- [ ] **2% + 2% split komissiya modeli:** Ommaviy ofertada ijarachidan 2% va mulkdor uy egasidan 2% xizmat haqi ushlab qolinishining huquqiy asosini tasdiqlash.
- [ ] **Mablag'larni vaqtincha saqlash (Eskrou/Nominal hisobvaraq):** 
  - O'zbekiston Respublikasi Markaziy Banki qoidalariga ko'ra, to'lov tashkiloti yoki bank litsenziyasisiz platformaning o'z hisobvarag'ida uchinchi shaxslar pulini saqlash xavfi mavjud.
  - **Tavsiya:** Partner tijorat banki (masalan, Ipak Yo'li Banki, Kapitalbank yoki Anorbank) bilan nominal/eskrou hisobvaraq (Escrow Account) ochish bo'yicha hamkorlik shartnomasini imzolash yoki rasmiy to'lov agenti agentlik shartnomasini tuzish.
- [ ] **Shaxsiy ma'lumotlarni qayta ishlash:** 
  - O'zR "Shaxsga doir ma'lumotlar to'g'risida"gi O'RQ-547-son Qonuniga muvofiq, foydalanuvchilarning Telegram ID, F.I.Sh., telefon raqami va kadastr hujjatlarini O'zbekiston hududida joylashgan serverlarda qayta ishlash va saqlash roziligini ommaviy ofertaga kiritish.
- [ ] **Talabalar uchun 12% soliq imtiyozi ifodasi:**
  - O'zR Soliq kodeksi 378-moddasi 19-bandiga havola keltirilgan holda, platforma faqat shablon va ko'mak berishi, `ijara.soliq.uz` tizimida ro'yxatdan o'tkazish majburiyati tomonlar zimmasida ekanligi, va bu yuridik maslahat hisoblanmasligi yozma tasdiqlanishi kerak.

---

## 2. To'lov Tizimlari Bilan Rasmiy Kelishuv (Click & Payme)
- [ ] **Ikki bosqichli to'lov (Two-step Pre-authorization/Hold):**
  - Click va Payme texnik departamentlari bilan yozma ravishda kelishish: 24 soatlik avtorizatsiyani (hold) qo'llab-quvvatlaydimi yoki to'lov zudlik bilan yechib olinib, 24 soat ichida tasdiqlanmasa, API orqali zudlik bilan komissiyasiz qaytariladimi (Refund)?
  - Click Merchant API va Payme Business integratsiya shartnomalarini yuridik shaxs (MChJ/YTT) nomiga rasmiylashtirish.
- [ ] **Avtomatlashtirilgan to'lov chiqimlari (Payouts / P2P API):**
  - Ko'chib kirish dalolatnomasi ikki tomonlama tasdiqlangach, mablag'ni uy egasining Uzcard/Humo kartasiga avtomatik o'tkazish (Mass Payment / Payout API) bo'yicha limitlar va tariflarni belgilash.

---

## 3. Dastlabki 30–50 ta Tranzaksiyani Boshqarish (Manual Mode)
- [ ] Dastlabki 30–50 ta ijara bitimi davomida xatolar va firibgarlik holatlarini bartaraf etish uchun `PAYMENT_MODE=manual` holatida ishlash.
- [ ] Har bir hold, to'lov va qaytarish holatini operator admin panel (`/admin`) orqali bank ko'chirmasi bilan solishtirib tasdiqlashi.
- [ ] Tranzaksiya jarayonidagi foydalanuvchi xatti-harakatlari va dalolatnoma sifatini tahlil qilib, so'ngra to'liq API avtomatizatsiyasiga o'tish.

---

## 4. Maxsus Domen va Telegram Bot Konfiguratsiyasi
- [ ] **Domen sotib olish:** Milliy `.uz` zonasida rasmiy domen xarid qilish (masalan, `renttrust.uz` yoki `rent-trust.uz`).
- [ ] **SSL va DNS:** Cloudflare yoki Render Custom Domains orqali domenni ulash, HTTPS sertifikatini sozlash.
- [ ] **BotFather sozlamalari:**
  - `@BotFather` orqali Web App URL manzilini yangi domenga yo'naltirish (`https://renttrust.uz`).
  - Bot menyusi buyruqlari (`/start`, `/search`, `/my_bookings`, `/help`) va tavsiflarini (About, Description) yangilash.
  - Short Name yaratish (masalan, `app` -> `https://t.me/RentTrust_Uz_Bot/app?startapp=...`).

---

## 5. Ishlab Chiqarish Infratuzilmasi (Production Hosting)
- [ ] **Render Paid Plan:** Render bepul tarifidagi 50 soniyalik "sovuq start" (cold start / spin-down) kutishlarini yo'qotish uchun Starter planiga ($7/oy) o'tish.
- [ ] **Frontendni ajratish (ixtiyoriy, trafik oshganda):** 
  - Statik HTML/CSS/JS frontendni Cloudflare Pages yoki Vercel ga bepul joylashtirib, backendni mustaqil Python REST API sifatida ajratish.
- [ ] **Zaxira nusxalar (Backups):** Supabase yoki PostgreSQL ma'lumotlar bazasining har kunlik avtomatik backup rejasini yoqish.

---

## 6. Qidiruv Tizimlari (SEO) Uchun Alohida Landing Sahifa
- [ ] Google va Yandex qidiruv tizimlarida Toshkentdagi ijarachilar va uy egalari platformani topishi uchun `renttrust.uz` bosh sahifasida yengil SEO-landing yaratish.
- [ ] Landing sahifada:
  - 2% xizmat haqi va an'anaviy maklerlar bilan farqlar jadvali;
  - Himoyalangan to'lov va depozit dalolatnomasi sxemasi;
  - "Telegramda ochish" tugmasi orqali to'g'ridan-to'g'ri Web App ga o'tish.

---

## 7. Talaba Soliq Imtiyozi Bo'yicha Yuridik Tasdiq
- [ ] Soliq maslahatchisi bilan kelishilgan yakuniy matn:
  > "Talabaga ijaraga bersangiz va shartnoma soliq organida ro'yxatdan o'tgan bo'lsa, ijaradan olingan daromad daromad solig'idan ozod bo'ladi. Bu yuridik maslahat emas."
- [ ] `ijara.soliq.uz` ga integratsiya qilish imkoniyatlarini o'rganish (davlat API ochiqligiga qarab kelgusida avtomatlashtirish).
