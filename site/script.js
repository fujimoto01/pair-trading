document.addEventListener('DOMContentLoaded', () => {
  // Typewriter effect for main title
  const typewriterTitle = () => {
    const title = document.querySelector('.main-title');
    if (!title) return;
    
    const text = title.textContent;
    title.textContent = '';
    title.style.opacity = '1';
    
    let i = 0;
    const typeInterval = setInterval(() => {
      title.textContent += text[i];
      i++;
      if (i >= text.length) {
        clearInterval(typeInterval);
        // Add cursor blink effect
        title.style.borderRight = '3px solid var(--accent)';
        setTimeout(() => {
          title.style.borderRight = 'none';
        }, 1000);
      }
    }, 80);
  };

  // Floating animation for context section
  const floatingAnimation = () => {
    const contextSection = document.querySelector('.context-section');
    if (contextSection) {
      let offset = 0;
      setInterval(() => {
        offset += 0.02;
        const y = Math.sin(offset) * 3;
        contextSection.style.transform = `translateY(${y}px)`;
      }, 50);
    }
  };

  // Interactive metrics with hover effects
  const interactiveMetrics = () => {
    document.querySelectorAll('.metric').forEach(metric => {
      metric.addEventListener('mouseenter', () => {
        metric.style.transform = 'translateY(-5px) scale(1.05)';
        metric.style.boxShadow = '0 15px 35px rgba(56,189,248,0.4)';
      });
      
      metric.addEventListener('mouseleave', () => {
        metric.style.transform = 'translateY(0) scale(1)';
        metric.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
      });
    });
  };

  // Smooth scroll for anchors
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const hash = a.getAttribute('href');
      const target = document.querySelector(hash);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

  // Progress bar
  const progress = document.createElement('div');
  progress.className = 'progress';
  document.body.appendChild(progress);
  const updateProgress = () => {
    const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const pct = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;
    progress.style.width = pct + '%';
  };
  window.addEventListener('scroll', updateProgress);
  updateProgress();

  // Initialize interactive features
  setTimeout(typewriterTitle, 500);
  setTimeout(floatingAnimation, 1000);
  setTimeout(interactiveMetrics, 1500);

  // Removido: toggle de tema (CTA 'Tema')

  // Reveal on scroll
  const revealEls = document.querySelectorAll('.reveal, .step, .card, .gallery figure');
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) e.target.classList.add('visible');
    });
  }, { threshold: 0.15 });
  revealEls.forEach(el => io.observe(el));

  // Animate metrics numbers in hero and results
  const animateNumber = (el, finalText, duration = 1200) => {
    // Detect percentage
    const isPct = /%$/.test(finalText);
    const numeric = parseFloat(finalText.replace(/[%,]/g, '').replace(',', '.'));
    let start = 0;
    const startTime = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - startTime) / duration);
      const val = start + (numeric - start) * t;
      const formatted = isPct ? (val.toFixed(2).replace('.', ',') + '%') : val.toFixed(2).replace('.', ',');
      el.textContent = formatted;
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = finalText; // snap
    };
    requestAnimationFrame(step);
  };
  document.querySelectorAll('.metrics .metric strong, [data-anim="metric"]').forEach(el => {
    animateNumber(el, el.textContent.trim());
  });

  // Parallax effect for hero content
  const hero = document.querySelector('.hero .container');
  const onParallax = () => {
    const y = (window.scrollY || 0);
    const offset = Math.max(0, 40 - y * 0.06);
    if (hero) hero.style.transform = `translateY(${offset}px)`;
  };
  window.addEventListener('scroll', onParallax);
  onParallax();

  // Lightbox for gallery images
  const galleryImgs = Array.from(document.querySelectorAll('.lightbox-target'));
  if (galleryImgs.length) {
    const overlay = document.createElement('div');
    overlay.className = 'lightbox';
    overlay.innerHTML = '<span class="close">✕</span>';
    const img = document.createElement('img');
    overlay.appendChild(img);
    document.body.appendChild(overlay);

    let current = 0;
    const open = (idx) => {
      current = idx;
      img.src = galleryImgs[current].src;
      overlay.classList.add('show');
    };
    const close = () => overlay.classList.remove('show');
    const next = () => open((current + 1) % galleryImgs.length);
    const prev = () => open((current - 1 + galleryImgs.length) % galleryImgs.length);

    galleryImgs.forEach((g, i) => {
      g.style.cursor = 'zoom-in';
      g.addEventListener('click', () => open(i));
    });
    overlay.querySelector('.close').addEventListener('click', close);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    window.addEventListener('keydown', (e) => {
      if (!overlay.classList.contains('show')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowRight') next();
      if (e.key === 'ArrowLeft') prev();
    });
  }
});