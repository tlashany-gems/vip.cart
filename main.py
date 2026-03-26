<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
<title>TALASHNY — رمضان القادم</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Cairo:wght@400;500;600;700;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"/>
<style>
:root{
  --gold1:#c8a84b;--gold2:#f5d070;--gold3:#8a6820;--gold4:#e8c060;--gold5:#fff1c0;
  --gold-glow:rgba(200,168,75,.35);
  --red:#e60000;
  --bg:#06050a;--l1:#0a0908;--l2:#100e08;--l3:#161208;--l4:#1c1808;
  --ink:#f0ead8;--ink2:#c8b880;--ink3:#7a6a40;
  --stroke:rgba(200,168,75,.12);--stroke2:rgba(200,168,75,.28);
  --green:#00C853;
  --r:18px;--r-sm:12px;
  --spring:cubic-bezier(.34,1.56,.64,1);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%;-webkit-font-smoothing:antialiased;}
body{
  font-family:'Cairo',sans-serif;background:var(--bg);color:var(--ink);overflow-x:hidden;touch-action:manipulation;
  background-image:
    radial-gradient(ellipse 80% 40% at 50% 0%,rgba(200,168,75,.18) 0%,rgba(200,168,75,.05) 45%,transparent 70%),
    radial-gradient(ellipse 50% 30% at 80% 100%,rgba(200,168,75,.08) 0%,transparent 60%);
  min-height:100vh;
}
*{-webkit-user-select:none;-moz-user-select:none;user-select:none;}

/* ══ SPLASH ══ */
#s-splash{
  position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;
  background:radial-gradient(ellipse 120% 80% at 50% -10%, #1a1200 0%, #0a0800 35%, #06050a 70%);
  z-index:9999;overflow:hidden;transition:opacity .8s ease;
}
#s-splash.fade-out{opacity:0;pointer-events:none;}

.sp-stars{position:absolute;inset:0;overflow:hidden;}
.sp-star{position:absolute;border-radius:50%;background:#fff;animation:starTwinkle var(--dur,3s) ease-in-out var(--delay,0s) infinite;}
@keyframes starTwinkle{0%,100%{opacity:var(--min-op,.1)}50%{opacity:var(--max-op,.8)}}

.sp-moon{position:absolute;top:6%;right:8%;width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#f5d070,#c8a84b);box-shadow:0 0 40px rgba(200,168,75,.6);overflow:hidden;animation:moonFloat 4s ease-in-out infinite;}
.sp-moon::before{content:'';position:absolute;top:-5px;right:-5px;width:48px;height:48px;border-radius:50%;background:#0a0800;}
@keyframes moonFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}

.sp-arch{position:absolute;top:-30px;left:50%;transform:translateX(-50%);width:280px;height:160px;border-radius:0 0 50% 50%;background:linear-gradient(180deg,rgba(200,168,75,.15) 0%,transparent 100%);border:1px solid rgba(200,168,75,.15);border-top:none;}

.sp-stage{position:relative;z-index:2;display:flex;flex-direction:column;align-items:center;gap:0;}

.sp-logo-wrap{position:relative;margin-bottom:32px;}
.sp-halo{position:absolute;inset:-28px;border-radius:50%;background:radial-gradient(circle,rgba(200,168,75,.3) 0%,transparent 70%);animation:haloPulse 2.8s ease-in-out infinite;}
@keyframes haloPulse{0%,100%{transform:scale(.9);opacity:.6}50%{transform:scale(1.1);opacity:1}}
.sp-spin-ring{position:absolute;inset:-10px;border-radius:50%;animation:spinRing 5s linear infinite;background:conic-gradient(from 0deg,rgba(200,168,75,0) 0deg,rgba(200,168,75,.9) 60deg,rgba(245,208,112,.7) 120deg,rgba(200,168,75,.9) 180deg,rgba(200,168,75,0) 240deg,rgba(200,168,75,0) 360deg);-webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 2px),black calc(100% - 2px));mask:radial-gradient(farthest-side,transparent calc(100% - 2px),black calc(100% - 2px));}
@keyframes spinRing{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
.sp-icon{position:relative;width:120px;height:120px;border-radius:30px;background:linear-gradient(145deg,#1a1400 0%,#2a2000 30%,#1a1400 100%);border:2px solid rgba(200,168,75,.4);box-shadow:0 0 0 1px rgba(200,168,75,.1),0 20px 60px rgba(0,0,0,.8),0 0 40px rgba(200,168,75,.2);display:flex;align-items:center;justify-content:center;overflow:hidden;animation:iconDrop .9s cubic-bezier(.34,1.45,.64,1) .15s both;}
@keyframes iconDrop{from{opacity:0;transform:scale(.25) rotate(-20deg)}to{opacity:1;transform:scale(1) rotate(0)}}
.sp-icon::before{content:'';position:absolute;top:0;left:0;right:0;height:50%;background:linear-gradient(180deg,rgba(200,168,75,.1) 0%,transparent 100%);border-radius:30px 30px 0 0;}
.sp-icon img{width:78px;height:78px;object-fit:contain;position:relative;z-index:1;filter:drop-shadow(0 4px 16px rgba(200,168,75,.5));}
.sp-bolt{position:absolute;bottom:-10px;right:-10px;width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#7a5c18,#f0cd60,#b8921e);border:3px solid #06050a;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px rgba(200,168,75,.7);animation:boltIn .6s cubic-bezier(.34,1.8,.64,1) 1.1s both;}
@keyframes boltIn{from{opacity:0;transform:scale(0) rotate(-60deg)}to{opacity:1;transform:scale(1) rotate(0)}}
.sp-bolt i{font-size:.65rem;color:#1a0e00;}

.sp-rk-badge{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,rgba(200,168,75,.1),rgba(200,168,75,.05));border:1px solid rgba(200,168,75,.25);border-radius:100px;padding:5px 14px;font-size:.6rem;font-weight:800;color:var(--gold2);letter-spacing:1px;margin-bottom:14px;animation:textIn .4s ease 1.2s both;box-shadow:0 0 20px rgba(200,168,75,.1);}
@keyframes textIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}

.sp-name{display:flex;align-items:baseline;gap:0;margin-bottom:6px;animation:textIn .6s ease .75s both;}
.sp-nl{font-family:'Playfair Display',serif;font-size:3.2rem;font-weight:900;line-height:.95;color:transparent;background:linear-gradient(160deg,#a07828 0%,#c8a84b 20%,#f5d070 40%,#e8c060 55%,#f5d070 65%,#c8a84b 80%,#8a6820 100%);background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:goldFlow 5s linear infinite,nlIn .5s cubic-bezier(.34,1.5,.64,1) both;animation-delay:0s,calc(.75s + var(--n)*.07s);}
@keyframes nlIn{from{opacity:0;transform:translateY(28px) scaleY(.4)}to{opacity:1;transform:none}}
@keyframes goldFlow{0%{background-position:200% center}100%{background-position:-200% center}}

.sp-divider{display:flex;align-items:center;gap:8px;margin:14px 0 10px;animation:textIn .4s ease 1.1s both;}
.sp-div-line{width:45px;height:1px;background:linear-gradient(90deg,transparent,rgba(200,168,75,.4),transparent);}
.sp-div-gem{width:6px;height:6px;background:var(--gold1);transform:rotate(45deg);box-shadow:0 0 8px var(--gold-glow);}
.sp-ramadan-label{font-family:'Cairo',sans-serif;font-size:.85rem;font-weight:800;color:transparent;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold4),var(--gold2),var(--gold3));background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:goldFlow 4s linear infinite,textIn .5s ease 1s both;margin-bottom:6px;}
.sp-sub{font-size:.6rem;font-weight:700;color:rgba(200,168,75,.4);letter-spacing:2px;animation:textIn .5s ease 1.3s both;}

.sp-foot{position:absolute;bottom:0;left:0;right:0;padding:0 28px 44px;}
.sp-bar-track{height:2px;background:rgba(200,168,75,.08);border-radius:2px;overflow:hidden;margin-bottom:14px;}
.sp-bar-fill{height:100%;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold4),var(--gold2));background-size:300%;animation:barGrow 2.4s cubic-bezier(.25,.46,.45,.94) .4s forwards,goldFlow 1.5s linear .4s infinite;width:0;}
@keyframes barGrow{0%{width:0%}30%{width:40%}65%{width:75%}85%{width:90%}100%{width:100%}}
.sp-meta{display:flex;align-items:center;justify-content:space-between;animation:textIn .4s ease 2s both;}
.sp-ver{font-size:.45rem;font-weight:700;color:rgba(200,168,75,.25);letter-spacing:1px;}
.sp-brand{display:flex;align-items:center;gap:5px;}
.sp-brand-dot{width:4px;height:4px;border-radius:50%;background:rgba(200,168,75,.4);}
.sp-brand-txt{font-size:.44rem;font-weight:800;letter-spacing:1.5px;color:rgba(200,168,75,.3);}

/* ══ BANNER ══ */
.banner{position:sticky;top:0;width:100%;background:rgba(6,5,10,.97);display:flex;justify-content:space-between;align-items:center;padding:0 16px;height:64px;z-index:100;border-bottom:1px solid var(--stroke);box-shadow:0 4px 30px rgba(0,0,0,.8);flex-shrink:0;}
.banner-left{display:flex;align-items:center;gap:10px;}
.banner-logo{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#1a1400,#2a2000);border:1px solid rgba(200,168,75,.25);display:flex;align-items:center;justify-content:center;box-shadow:0 0 16px rgba(200,168,75,.2);overflow:hidden;}
.banner-logo img{width:24px;height:24px;object-fit:contain;filter:drop-shadow(0 2px 6px rgba(200,168,75,.5));}
.banner-letters{display:flex;font-size:1.1rem;font-weight:900;letter-spacing:5px;}
.banner-letters span{display:inline-block;color:transparent;background:linear-gradient(90deg,#7a5c18 0%,#c8a84b 20%,#f5d070 40%,#e8c060 60%,#f5d070 75%,#8a6820 100%);background-size:400% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:goldFlow 4s linear infinite;animation-delay:calc(var(--i)*.18s);}
.banner-right{display:flex;flex-direction:column;align-items:flex-end;gap:2px;}
.banner-tag{font-size:.52rem;font-weight:700;color:var(--ink3);letter-spacing:1px;}
.banner-season{font-size:.62rem;font-weight:800;color:var(--gold2);}

/* ══ MAIN PAGE ══ */
.page-wrap{max-width:480px;margin:0 auto;padding:20px 14px 100px;}

/* ══ ENDED CARD ══ */
.ended-card{
  background:var(--l1);border:1px solid var(--stroke2);border-radius:22px;
  padding:28px 20px;text-align:center;margin-bottom:14px;position:relative;overflow:hidden;
  animation:cardIn .5s cubic-bezier(.34,1.2,.64,1) both;
}
@keyframes cardIn{from{opacity:0;transform:translateY(24px) scale(.97)}to{opacity:1;transform:none}}
.ended-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold4),var(--gold2),var(--gold3));}
.ended-card::after{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 0%,rgba(200,168,75,.07) 0%,transparent 70%);pointer-events:none;}

.ended-moon-icon{font-size:3rem;margin-bottom:10px;display:block;filter:drop-shadow(0 0 20px rgba(200,168,75,.5));animation:moonBob 3s ease-in-out infinite;}
@keyframes moonBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}

.ended-title{font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:900;color:transparent;background:linear-gradient(135deg,#a07828,#f5d070,#c8a84b);background-size:300%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:goldFlow 5s linear infinite;margin-bottom:6px;}
.ended-subtitle{font-size:.75rem;font-weight:700;color:var(--ink2);margin-bottom:16px;line-height:1.6;}
.ended-line{height:1px;background:linear-gradient(90deg,transparent,rgba(200,168,75,.3),transparent);margin:16px 0;}
.ended-note{font-size:.68rem;color:var(--ink3);line-height:1.7;direction:rtl;}
.ended-note b{color:var(--gold2);font-weight:800;}

/* ══ COUNTDOWN ══ */
.countdown-card{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);padding:20px 16px;margin-bottom:14px;animation:cardIn .5s cubic-bezier(.34,1.2,.64,1) .08s both;}
.cd-label{font-size:.54rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);text-align:center;margin-bottom:16px;display:flex;align-items:center;gap:8px;justify-content:center;}
.cd-label-line{width:30px;height:1px;background:linear-gradient(90deg,transparent,rgba(200,168,75,.35),transparent);}
.cd-label-gem{width:5px;height:5px;background:var(--gold1);transform:rotate(45deg);}

.cd-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;}
.cd-unit{background:var(--l2);border:1px solid var(--stroke);border-radius:var(--r-sm);padding:14px 6px 10px;text-align:center;position:relative;overflow:hidden;}
.cd-unit::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold3));}
.cd-num{font-family:'Playfair Display',serif;font-size:2.1rem;font-weight:900;color:var(--gold2);line-height:1;transition:all .3s cubic-bezier(.34,1.4,.64,1);}
.cd-num.pop{animation:numPop .3s cubic-bezier(.34,1.6,.64,1);}
@keyframes numPop{0%{transform:scale(.7);opacity:.4}100%{transform:scale(1);opacity:1}}
.cd-lbl{font-size:.5rem;font-weight:700;color:var(--ink3);letter-spacing:.8px;margin-top:5px;}

.cd-date-row{display:flex;align-items:center;justify-content:center;gap:7px;margin-top:14px;padding-top:12px;border-top:1px solid var(--stroke);}
.cd-date-chip{display:inline-flex;align-items:center;gap:5px;background:rgba(200,168,75,.07);border:1px solid rgba(200,168,75,.15);border-radius:100px;padding:5px 14px;font-size:.62rem;font-weight:800;color:var(--gold2);}
.cd-date-chip i{font-size:.55rem;color:var(--gold1);}

/* ══ PROGRESS BAR ══ */
.progress-card{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);padding:16px;margin-bottom:14px;animation:cardIn .5s cubic-bezier(.34,1.2,.64,1) .16s both;}
.prog-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;}
.prog-label{font-size:.6rem;font-weight:700;color:var(--ink2);}
.prog-pct{font-size:.6rem;font-weight:800;color:var(--gold2);}
.prog-track{height:6px;background:rgba(255,255,255,.05);border-radius:3px;overflow:hidden;}
.prog-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold4));transition:width 1.2s cubic-bezier(.25,.46,.45,.94);}
.prog-note{font-size:.54rem;color:var(--ink3);margin-top:8px;text-align:center;}

/* ══ STATUS CARD ══ */
.status-card{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);padding:18px;margin-bottom:14px;animation:cardIn .5s cubic-bezier(.34,1.2,.64,1) .24s both;}
.status-row{display:flex;align-items:center;gap:12px;}
.status-icon-wrap{width:44px;height:44px;border-radius:12px;background:rgba(200,168,75,.08);border:1px solid rgba(200,168,75,.15);display:flex;align-items:center;justify-content:center;color:var(--gold1);font-size:1rem;flex-shrink:0;}
.status-body{}
.status-title{font-size:.78rem;font-weight:800;color:var(--ink);margin-bottom:4px;}
.status-text{font-size:.62rem;color:var(--ink2);line-height:1.6;}
.status-text b{color:var(--gold2);font-weight:800;}

/* ══ CONTACT BUTTONS ══ */
.contact-title{font-size:.54rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);text-align:center;margin-bottom:10px;display:flex;align-items:center;gap:8px;justify-content:center;}
.contact-title::before,.contact-title::after{content:'';flex:1;height:1px;background:var(--stroke);}
.contact-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;animation:cardIn .5s cubic-bezier(.34,1.2,.64,1) .32s both;}
.contact-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;padding:14px 8px;background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r-sm);text-decoration:none;transition:all .25s;cursor:pointer;}
.contact-btn:hover{border-color:var(--stroke2);background:rgba(200,168,75,.04);}
.contact-btn:active{transform:scale(.95);}
.contact-btn .cb-icon{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:.95rem;transition:all .2s;}
.contact-btn.tg .cb-icon{background:rgba(41,182,246,.1);color:#29b6f6;border:1px solid rgba(41,182,246,.2);}
.contact-btn.wa .cb-icon{background:rgba(37,211,102,.1);color:#25d366;border:1px solid rgba(37,211,102,.2);}
.contact-btn.fb .cb-icon{background:rgba(24,119,242,.1);color:#1877f2;border:1px solid rgba(24,119,242,.2);}
.contact-btn .cb-label{font-size:.52rem;font-weight:700;color:var(--ink3);}

/* ══ FOOTER ══ */
.footer{text-align:center;padding:10px 0 20px;}
.footer-brand{display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:6px;}
.footer-dot{width:4px;height:4px;border-radius:50%;background:rgba(200,168,75,.3);}
.footer-name{font-family:'Playfair Display',serif;font-size:.75rem;font-weight:700;color:rgba(200,168,75,.4);letter-spacing:3px;}
.footer-copy{font-size:.5rem;color:var(--ink3);}

/* ══ BOTTOM NAV ══ */
.botnav{position:fixed;bottom:0;left:0;right:0;height:60px;background:rgba(6,5,10,.97);backdrop-filter:blur(22px);border-top:1px solid var(--stroke);display:flex;justify-content:space-around;align-items:stretch;z-index:400;}
.nav-link{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;text-decoration:none;color:var(--ink3);font-family:'Cairo',sans-serif;font-size:.49rem;font-weight:700;letter-spacing:.5px;border-top:2px solid transparent;transition:color .2s,border-color .2s;}
.nav-link:hover{color:var(--gold1);border-color:var(--gold1);}
.nav-link i{font-size:1.05rem;}

/* Lanterns */
.sp-lantern{position:absolute;animation:lanternSway var(--sw,6s) ease-in-out var(--sd,0s) infinite;}
@keyframes lanternSway{0%,100%{transform:rotate(-8deg)}50%{transform:rotate(8deg)}}
.sp-lantern svg{filter:drop-shadow(0 0 12px rgba(200,168,75,.8));}
</style>
</head>
<body>

<!-- ══ SPLASH ══ -->
<div id="s-splash">
  <div class="sp-stars" id="spStars"></div>
  <div class="sp-moon"></div>
  <div class="sp-lantern" style="top:8%;left:5%;--sw:5s;--sd:0s">
    <svg width="22" height="38" viewBox="0 0 22 38" fill="none">
      <line x1="11" y1="0" x2="11" y2="6" stroke="rgba(200,168,75,.5)" stroke-width="1.5"/>
      <rect x="3" y="6" width="16" height="22" rx="4" fill="rgba(200,168,75,.12)" stroke="rgba(200,168,75,.6)" stroke-width="1"/>
      <ellipse cx="11" cy="6" rx="5" ry="2" fill="rgba(200,168,75,.3)" stroke="rgba(200,168,75,.6)" stroke-width="1"/>
      <line x1="11" y1="28" x2="11" y2="36" stroke="rgba(200,168,75,.4)" stroke-width="1"/>
      <ellipse cx="11" cy="36" rx="3" ry="1.5" fill="rgba(200,168,75,.3)"/>
    </svg>
  </div>
  <div class="sp-lantern" style="top:6%;right:15%;--sw:7s;--sd:1.5s">
    <svg width="18" height="30" viewBox="0 0 18 30" fill="none">
      <line x1="9" y1="0" x2="9" y2="5" stroke="rgba(200,168,75,.4)" stroke-width="1.2"/>
      <rect x="2" y="5" width="14" height="17" rx="3" fill="rgba(200,168,75,.1)" stroke="rgba(200,168,75,.5)" stroke-width="1"/>
      <ellipse cx="9" cy="5" rx="4" ry="1.5" fill="rgba(200,168,75,.25)" stroke="rgba(200,168,75,.5)" stroke-width="1"/>
      <line x1="9" y1="22" x2="9" y2="28" stroke="rgba(200,168,75,.3)" stroke-width="1"/>
    </svg>
  </div>
  <div class="sp-arch"></div>

  <div class="sp-stage">
    <div class="sp-logo-wrap">
      <div class="sp-halo"></div>
      <div class="sp-spin-ring"></div>
      <div class="sp-icon">
        <img src="https://i.postimg.cc/PqxnBbpw/vodafone2.png" alt="Vodafone"
             onerror="this.style.display='none';this.parentElement.innerHTML+='<i class=\'fas fa-star\' style=\'font-size:2.5rem;color:#c8a84b\'></i>'"/>
      </div>
      <div class="sp-bolt"><i class="fas fa-star"></i></div>
    </div>
    <div class="sp-rk-badge"><i class="fas fa-star-and-crescent"></i>&nbsp;TALASHNY</div>
    <div class="sp-name">
      <span class="sp-nl" style="--n:0">Y</span><span class="sp-nl" style="--n:1">N</span>
      <span class="sp-nl" style="--n:2">H</span><span class="sp-nl" style="--n:3">S</span>
      <span class="sp-nl" style="--n:4">A</span><span class="sp-nl" style="--n:5">L</span>
      <span class="sp-nl" style="--n:6">A</span><span class="sp-nl" style="--n:7">T</span>
    </div>
    <div class="sp-divider">
      <div class="sp-div-line"></div><div class="sp-div-gem"></div><div class="sp-div-line"></div>
    </div>
    <div class="sp-ramadan-label">كروت رمضان فودافون</div>
    <div class="sp-sub">نراكم في رمضان القادم</div>
  </div>

  <div class="sp-foot">
    <div class="sp-bar-track"><div class="sp-bar-fill"></div></div>
    <div class="sp-meta">
      <div class="sp-ver">v2.1 · Vodafone EG</div>
      <div class="sp-brand">
        <div class="sp-brand-dot"></div>
        <div class="sp-brand-txt">TALASHNY</div>
        <div class="sp-brand-dot"></div>
      </div>
    </div>
  </div>
</div>

<!-- ══ MAIN APP ══ -->
<div id="s-app" style="display:none;min-height:100vh">
  <div class="banner">
    <div class="banner-left">
      <div class="banner-logo">
        <img src="https://i.postimg.cc/PqxnBbpw/vodafone2.png" alt=""
             onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\'fas fa-star\' style=\'color:var(--gold1);font-size:.9rem\'></i>'"/>
      </div>
      <div class="banner-letters">
        <span style="--i:0">Y</span><span style="--i:1">N</span><span style="--i:2">H</span>
        <span style="--i:3">S</span><span style="--i:4">A</span><span style="--i:5">L</span>
        <span style="--i:6">A</span><span style="--i:7">T</span>
      </div>
    </div>
    <div class="banner-right">
      <div class="banner-season">رمضان 2026</div>
      <div class="banner-tag">قريباً إن شاء الله</div>
    </div>
  </div>

  <div class="page-wrap">

    <!-- Ended card -->
    <div class="ended-card">
      <span class="ended-moon-icon">🌙</span>
      <div class="ended-title">انتهت كروت رمضان 1446</div>
      <div class="ended-subtitle">
        شكراً لكل من استخدم TALASHNY هذا الموسم<br>
        كانت رحلة رائعة معكم 💛
      </div>
      <div class="ended-line"></div>
      <div class="ended-note">
        خدمة <b>شحن كروت رمضان فودافون</b> متاحة بس خلال شهر رمضان المبارك.<br>
        هنعود بشكل أقوى في <b>رمضان القادم 2026</b> إن شاء الله.
      </div>
    </div>

    <!-- Countdown -->
    <div class="countdown-card">
      <div class="cd-label">
        <div class="cd-label-line"></div>
        <div class="cd-label-gem"></div>
        العد التنازلي لرمضان 1447
        <div class="cd-label-gem"></div>
        <div class="cd-label-line"></div>
      </div>
      <div class="cd-grid">
        <div class="cd-unit">
          <div class="cd-num" id="cd-days">---</div>
          <div class="cd-lbl">يوم</div>
        </div>
        <div class="cd-unit">
          <div class="cd-num" id="cd-hours">--</div>
          <div class="cd-lbl">ساعة</div>
        </div>
        <div class="cd-unit">
          <div class="cd-num" id="cd-mins">--</div>
          <div class="cd-lbl">دقيقة</div>
        </div>
        <div class="cd-unit">
          <div class="cd-num" id="cd-secs">--</div>
          <div class="cd-lbl">ثانية</div>
        </div>
      </div>
      <div class="cd-date-row">
        <div class="cd-date-chip">
          <i class="fas fa-calendar-star"></i>
          المتوقع: ~20 فبراير 2026
        </div>
      </div>
    </div>

    <!-- Progress -->
    <div class="progress-card">
      <div class="prog-row">
        <div class="prog-label"><i class="fas fa-hourglass-half" style="color:var(--gold1);margin-left:5px"></i>الوقت المتبقي من السنة حتى رمضان</div>
        <div class="prog-pct" id="prog-pct">—%</div>
      </div>
      <div class="prog-track">
        <div class="prog-fill" id="prog-fill" style="width:0%"></div>
      </div>
      <div class="prog-note" id="prog-note">جاري الحساب...</div>
    </div>

    <!-- Status -->
    <div class="status-card">
      <div class="status-row">
        <div class="status-icon-wrap"><i class="fas fa-bell-slash"></i></div>
        <div class="status-body">
          <div class="status-title">الخدمة متوقفة مؤقتاً</div>
          <div class="status-text">
            كروت رمضان من فودافون بتتاح بس خلال شهر رمضان المبارك.<br>
            <b>هنعود قبل رمضان بإشعار فوري</b> — ابقى متابعنا!
          </div>
        </div>
      </div>
    </div>

    <!-- Contact -->
    <div class="contact-title">تواصل معنا</div>
    <div class="contact-grid">
      <a href="https://t.me/FY_TF" target="_blank" class="contact-btn tg">
        <div class="cb-icon"><i class="fab fa-telegram-plane"></i></div>
        <div class="cb-label">تيليجرام</div>
      </a>
      <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank" class="contact-btn wa">
        <div class="cb-icon"><i class="fab fa-whatsapp"></i></div>
        <div class="cb-label">واتساب</div>
      </a>
      <a href="https://www.facebook.com/VI808IV" target="_blank" class="contact-btn fb">
        <div class="cb-icon"><i class="fab fa-facebook-f"></i></div>
        <div class="cb-label">فيسبوك</div>
      </a>
    </div>

    <!-- Footer -->
    <div class="footer">
      <div class="footer-brand">
        <div class="footer-dot"></div>
        <div class="footer-name">TALASHNY</div>
        <div class="footer-dot"></div>
      </div>
      <div class="footer-copy">© 2025 · كروت رمضان فودافون · نراكم العام القادم</div>
    </div>
  </div>

  <nav class="botnav">
    <a href="https://t.me/FY_TF" target="_blank" class="nav-link"><i class="fab fa-telegram-plane"></i><span>تيليجرام</span></a>
    <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank" class="nav-link"><i class="fab fa-whatsapp"></i><span>واتساب</span></a>
    <a href="https://www.facebook.com/VI808IV" target="_blank" class="nav-link"><i class="fab fa-facebook-f"></i><span>فيسبوك</span></a>
  </nav>
</div>

<script>
// Stars
(function(){
  const wrap=document.getElementById('spStars');
  for(let i=0;i<60;i++){
    const s=document.createElement('div');s.className='sp-star';
    const sz=Math.random()*2+0.5;
    s.style.cssText=`width:${sz}px;height:${sz}px;top:${Math.random()*100}%;left:${Math.random()*100}%;--dur:${(Math.random()*3+2).toFixed(1)}s;--delay:${(Math.random()*4).toFixed(1)}s;--min-op:${(Math.random()*0.15).toFixed(2)};--max-op:${(Math.random()*0.6+0.2).toFixed(2)};`;
    wrap.appendChild(s);
  }
})();

// Splash → App
setTimeout(()=>{
  const splash=document.getElementById('s-splash');
  splash.classList.add('fade-out');
  setTimeout(()=>{
    splash.style.display='none';
    document.getElementById('s-app').style.display='block';
    startCountdown();updateProgress();
  },800);
},3000);

// Target: ~20 Feb 2026 (approximate start of Ramadan 1447)
const RAMADAN_TARGET = new Date('2026-02-20T00:00:00');

function pad(n){return String(n).padStart(2,'0');}

let prevSecs=-1;
function startCountdown(){
  function tick(){
    const now=new Date();
    const diff=RAMADAN_TARGET-now;
    if(diff<=0){
      document.getElementById('cd-days').textContent='0';
      document.getElementById('cd-hours').textContent='00';
      document.getElementById('cd-mins').textContent='00';
      document.getElementById('cd-secs').textContent='00';
      return;
    }
    const days=Math.floor(diff/86400000);
    const hours=Math.floor((diff%86400000)/3600000);
    const mins=Math.floor((diff%3600000)/60000);
    const secs=Math.floor((diff%60000)/1000);

    document.getElementById('cd-days').textContent=days;
    document.getElementById('cd-hours').textContent=pad(hours);
    document.getElementById('cd-mins').textContent=pad(mins);

    const secEl=document.getElementById('cd-secs');
    if(secs!==prevSecs){
      prevSecs=secs;
      secEl.textContent=pad(secs);
      secEl.classList.remove('pop');
      void secEl.offsetWidth;
      secEl.classList.add('pop');
    }
  }
  tick();setInterval(tick,1000);
}

function updateProgress(){
  // From end of Ramadan 2025 (~Mar 30 2025) to Ramadan 2026 (~Feb 20 2026)
  const start=new Date('2025-03-30T00:00:00');
  const end=RAMADAN_TARGET;
  const now=new Date();
  const total=end-start;
  const elapsed=now-start;
  const pct=Math.min(100,Math.max(0,Math.round(elapsed/total*100)));
  const remaining=Math.max(0,Math.floor((end-now)/86400000));

  document.getElementById('prog-fill').style.width=pct+'%';
  document.getElementById('prog-pct').textContent=pct+'%';

  let note='';
  if(remaining>180) note='لسه وقت كتير — استمتع بالأيام العادية 😄';
  else if(remaining>60) note='الوقت بيمشي بسرعة — متابعنا وهنعيد قريب!';
  else if(remaining>14) note='رمضان اقترب! جهّز نفسك 🌙';
  else note='رمضان على الأبواب! 🎉';
  document.getElementById('prog-note').textContent=note;
}
</script>
</body>
</html>
