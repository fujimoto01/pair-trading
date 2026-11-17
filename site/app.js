/* Project page: language, theme and charts.
   Charts are plain SVG drawn from window.PT_DATA (site/data.js),
   which is written by run_walkforward.py. */
(function () {
  'use strict';

  var D = window.PT_DATA;
  var root = document.documentElement;
  var body = document.body;
  var NS = 'http://www.w3.org/2000/svg';
  var MONTHS = {
    en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    pt: ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
  };

  function lang() { return body.getAttribute('data-lang') === 'pt' ? 'pt' : 'en'; }
  function tr(en, pt) { return lang() === 'pt' ? pt : en; }
  function num(v, digits) {
    return v.toLocaleString(lang() === 'pt' ? 'pt-BR' : 'en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }
  function pct(v, digits, signed) {
    var s = num(Math.abs(v) * 100, digits) + '%';
    if (v < 0) return '−' + s;
    return signed ? '+' + s : s;
  }
  function fmtDate(iso) {
    var p = iso.split('-');
    var m = MONTHS[lang()][+p[1] - 1];
    return lang() === 'pt' ? (+p[2]) + ' ' + m + ' ' + p[0] : m + ' ' + (+p[2]) + ', ' + p[0];
  }
  function fmtMonth(iso) {
    var p = iso.split('-');
    return MONTHS[lang()][+p[1] - 1] + ' ' + p[0].slice(2);
  }
  function days(iso) { return Date.parse(iso + 'T00:00:00Z') / 864e5; }

  function svg(tag, attrs, parent, text) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function scale(d0, d1, r0, r1) {
    return function (v) { return r0 + (v - d0) / (d1 - d0) * (r1 - r0); };
  }
  function path(xs, ys) {
    var out = '';
    for (var i = 0; i < xs.length; i++) {
      if (ys[i] == null) continue;
      out += (out ? 'L' : 'M') + xs[i].toFixed(1) + ' ' + ys[i].toFixed(1);
    }
    return out;
  }
  function niceTicks(lo, hi, n) {
    var span = hi - lo, step = Math.pow(10, Math.floor(Math.log10(span / n)));
    var err = span / n / step;
    step *= err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
    var t = [], v = Math.ceil(lo / step) * step;
    for (; v <= hi + 1e-9; v += step) t.push(+v.toFixed(10));
    return t;
  }
  function start(id, height) {
    var box = document.getElementById(id);
    if (!box) return null;
    box.innerHTML = '';
    var w = Math.max(300, box.clientWidth);
    var s = svg('svg', { viewBox: '0 0 ' + w + ' ' + height, width: w, height: height, role: 'img' }, box);
    return { box: box, svg: s, w: w, h: height, narrow: w < 480 };
  }

  /* hover: vertical rule and a small readout that follows the pointer */
  function hover(c, x0, x1, top, bottom, n, xOf, render) {
    var rule = svg('line', { y1: top, y2: bottom, class: 'rule', visibility: 'hidden' }, c.svg);
    var tip = document.createElement('div');
    tip.className = 'tip';
    tip.hidden = true;
    c.box.appendChild(tip);
    var hit = svg('rect', { x: x0, y: top, width: x1 - x0, height: bottom - top, fill: 'transparent' }, c.svg);
    function move(ev) {
      var r = c.svg.getBoundingClientRect();
      var px = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
      var i = Math.round((px - x0) / (x1 - x0) * (n - 1));
      i = Math.max(0, Math.min(n - 1, i));
      var x = xOf(i);
      rule.setAttribute('x1', x); rule.setAttribute('x2', x); rule.setAttribute('visibility', 'visible');
      tip.innerHTML = render(i);
      tip.hidden = false;
      var tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(c.w - tw, x + (x + tw + 14 > c.w ? -tw - 10 : 10))) + 'px';
      tip.style.top = top + 'px';
    }
    function leave() { rule.setAttribute('visibility', 'hidden'); tip.hidden = true; }
    hit.addEventListener('mousemove', move);
    hit.addEventListener('touchstart', move, { passive: true });
    hit.addEventListener('touchmove', move, { passive: true });
    hit.addEventListener('mouseleave', leave);
    hit.addEventListener('touchend', leave);
  }

  function monthTicks(c, dates, x, y, every) {
    var last = null;
    for (var i = 0; i < dates.length; i++) {
      var key = dates[i].slice(0, 7);
      if (key === last) continue;
      last = key;
      if ((+dates[i].slice(5, 7) - 1) % every !== 0 || i === 0) continue;
      svg('line', { x1: x(i), x2: x(i), y1: y, y2: y + 4, class: 'axis' }, c.svg);
      svg('text', { x: x(i), y: y + 16, class: 'tick', 'text-anchor': 'middle' }, c.svg, fmtMonth(dates[i]));
    }
  }

  /* 1. one pair: prices above, z-score and trades below */
  function drawExample() {
    var c = start('fig-example', 400);
    if (!c) return;
    var e = D.example, n = e.dates.length;
    var L = 34, R = c.narrow ? 46 : 58, x = scale(0, n - 1, L, c.w - R);
    var xi = function (i) { return x(i); };
    var topA = 14, topB = 178, botA = 222, botB = 366;
    var idx = e.dates.map(function (_, i) { return x(i); });

    var all = e.price_a.concat(e.price_b);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var yp = scale(lo - 2, hi + 2, topB, topA);
    var zmax = Math.max(3.2, Math.max.apply(null, e.z.map(Math.abs)) + 0.3);
    var yz = scale(-zmax, zmax, botB, botA);

    e.trades.forEach(function (t) {
      var i0 = e.dates.indexOf(t.entry), i1 = e.dates.indexOf(t.exit);
      if (i0 < 0 || i1 < 0) return;
      svg('rect', { x: x(i0), y: topA, width: Math.max(1, x(i1) - x(i0)), height: botB - topA, class: 'span' }, c.svg);
    });

    niceTicks(lo, hi, 3).forEach(function (v) {
      svg('line', { x1: L, x2: c.w - R, y1: yp(v), y2: yp(v), class: 'grid' }, c.svg);
      svg('text', { x: L - 6, y: yp(v) + 4, class: 'tick', 'text-anchor': 'end' }, c.svg, v);
    });
    svg('path', { d: path(idx, e.price_b.map(yp)), class: 'line muted' }, c.svg);
    svg('path', { d: path(idx, e.price_a.map(yp)), class: 'line' }, c.svg);
    var ya = yp(e.price_a[n - 1]), yb = yp(e.price_b[n - 1]);
    if (Math.abs(ya - yb) < 13) { var mid = (ya + yb) / 2, up = ya < yb ? -1 : 1; ya = mid + up * 6.5; yb = mid - up * 6.5; }
    svg('text', { x: c.w - R + 6, y: ya + 4, class: 'label' }, c.svg, e.a);
    svg('text', { x: c.w - R + 6, y: yb + 4, class: 'label muted' }, c.svg, e.b);
    svg('text', { x: L, y: topA - 2, class: 'cap' }, c.svg, tr('Price, start of window = 100', 'Preço, início da janela = 100'));

    var entry = D.config.entry_z;
    [-entry, 0, entry].forEach(function (v) {
      svg('line', { x1: L, x2: c.w - R, y1: yz(v), y2: yz(v), class: v === 0 ? 'axis' : 'band' }, c.svg);
      svg('text', { x: L - 6, y: yz(v) + 4, class: 'tick', 'text-anchor': 'end' }, c.svg, (v > 0 ? '+' : v < 0 ? '−' : '') + num(Math.abs(v), v === 0 ? 0 : 1));
    });
    svg('text', { x: c.w - R + 6, y: yz(entry) + 4, class: 'label accent' }, c.svg, tr('sell', 'vende'));
    svg('text', { x: c.w - R + 6, y: yz(-entry) + 4, class: 'label accent' }, c.svg, tr('buy', 'compra'));
    svg('path', { d: path(idx, e.z.map(function (v) { return v == null ? null : yz(v); })), class: 'line' }, c.svg);
    e.trades.forEach(function (t) {
      [t.entry, t.exit].forEach(function (d, k) {
        var i = e.dates.indexOf(d);
        if (i >= 0 && e.z[i] != null) svg('circle', { cx: x(i), cy: yz(e.z[i]), r: 3.5, class: k ? 'dot open' : 'dot' }, c.svg);
      });
    });
    svg('text', { x: L, y: botA - 10, class: 'cap' }, c.svg, tr('Z-score of the spread', 'Z-score do spread'));
    monthTicks(c, e.dates, xi, botB, c.narrow ? 2 : 1);

    hover(c, L, c.w - R, topA, botB, n, xi, function (i) {
      return '<b>' + fmtDate(e.dates[i]) + '</b>' + e.a + ' ' + num(e.price_a[i], 1) + '<br>' + e.b + ' ' + num(e.price_b[i], 1) +
        '<br>z ' + (e.z[i] == null ? '–' : num(e.z[i], 2).replace('-', '−'));
    });
  }

  /* 2. selection funnel: average number of pairs left after each filter */
  function drawFunnel() {
    var stages = [
      ['tested', tr('Pairs tested', 'Pares testados')],
      ['cointegrated', tr('Cointegrated', 'Cointegrados')],
      ['hurst', tr('Hurst below 0.5', 'Hurst abaixo de 0,5')],
      ['crossings', tr('Enough crossings', 'Cruzamentos suficientes')],
      ['tail', tr('Tail dependence', 'Dependência de cauda')],
      ['selected', tr('Traded', 'Operados')]
    ];
    var box = document.getElementById('fig-funnel');
    if (!box) return;
    var stacked = box.clientWidth < 480, rowH = stacked ? 46 : 34;
    var c = start('fig-funnel', stages.length * rowH + 6);
    var W = D.windows, labelW = stacked ? 0 : 190, numW = stacked ? 100 : 120, barY = stacked ? 20 : 2;
    var x = scale(0, W[0].funnel.tested, 0, c.w - labelW - numW);
    stages.forEach(function (s, k) {
      var vals = W.map(function (w) { return w.funnel[s[0]]; });
      var mean = vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
      var y = k * rowH + 6;
      svg('text', { x: 0, y: y + (stacked ? 12 : 15), class: 'label' }, c.svg, s[1]);
      svg('rect', { x: labelW, y: y + barY, width: Math.max(2, x(mean)), height: 18, class: k === stages.length - 1 ? 'bar accent' : 'bar' }, c.svg);
      var txt = num(Math.round(mean), 0);
      if (k > 0) txt += '  ·  ' + pct(mean / W[0].funnel.tested, mean / W[0].funnel.tested < 0.1 ? 1 : 0);
      svg('text', { x: labelW + Math.max(2, x(mean)) + 8, y: y + barY + 14, class: 'value' }, c.svg, txt);
    });
  }

  /* 3. walk-forward windows on a time axis */
  function drawWindows() {
    var W = D.windows, rowH = 20, top = 24, c = start('fig-windows', top + W.length * rowH + 8);
    if (!c) return;
    var R = 58, x = scale(days(W[0].formation_start), days(W[W.length - 1].trade_end), 0, c.w - R);
    for (var yv = 2014; yv <= 2021; yv++) {
      var xx = x(days(yv + '-01-01'));
      if (xx < -1 || xx > c.w - R + 1) continue;
      svg('line', { x1: xx, x2: xx, y1: top - 6, y2: c.h - 4, class: 'grid' }, c.svg);
      if (yv <= 2020) svg('text', { x: xx + 4, y: 12, class: 'tick' }, c.svg, yv);
    }
    W.forEach(function (w, k) {
      var y = top + k * rowH;
      var f0 = x(days(w.formation_start)), f1 = x(days(w.trade_start)), t1 = x(days(w.trade_end));
      svg('rect', { x: f0, y: y + 3, width: f1 - f0, height: rowH - 8, class: 'formation' }, c.svg);
      svg('rect', { x: f1, y: y + 3, width: t1 - f1, height: rowH - 8, class: w.ret >= 0 ? 'bar' : 'bar accent' }, c.svg);
      svg('text', { x: t1 + 6, y: y + rowH - 6, class: 'value' }, c.svg, pct(w.ret, 1, true));
    });
  }

  /* 4. equity curve and drawdown */
  function drawEquity() {
    var c = start('fig-equity', 330);
    if (!c) return;
    var cv = D.curve, n = cv.dates.length, L = 34, R = 12;
    var x = scale(0, n - 1, L, c.w - R), xi = function (i) { return x(i); };
    var idx = cv.dates.map(function (_, i) { return x(i); });
    var lo = Math.min.apply(null, cv.strategy.concat([100])), hi = Math.max.apply(null, cv.strategy.concat([100]));
    var pad = (hi - lo) * 0.08, topA = 14, topB = 210, botA = 246, botB = 300;
    var y = scale(lo - pad, hi + pad, topB, topA);
    niceTicks(lo, hi, 4).forEach(function (v) {
      svg('line', { x1: L, x2: c.w - R, y1: y(v), y2: y(v), class: v === 100 ? 'axis' : 'grid' }, c.svg);
      svg('text', { x: L - 6, y: y(v) + 4, class: 'tick', 'text-anchor': 'end' }, c.svg, v);
    });
    svg('path', { d: path(idx, cv.strategy.map(y)), class: 'line' }, c.svg);
    svg('text', { x: L, y: topA - 2, class: 'cap' }, c.svg, tr('Portfolio value, start = 100', 'Valor da carteira, início = 100'));

    var ddMin = Math.min.apply(null, cv.drawdown), yd = scale(0, Math.min(ddMin, -1), botA, botB);
    svg('path', { d: path(idx, cv.drawdown.map(yd)) + 'L' + x(n - 1).toFixed(1) + ' ' + botA + 'L' + L + ' ' + botA + 'Z', class: 'area' }, c.svg);
    svg('line', { x1: L, x2: c.w - R, y1: botA, y2: botA, class: 'axis' }, c.svg);
    svg('text', { x: L - 6, y: botB + 4, class: 'tick', 'text-anchor': 'end' }, c.svg, num(ddMin, 0).replace('-', '−') + '%');
    svg('text', { x: L, y: botA - 8, class: 'cap' }, c.svg, tr('Drawdown from the previous peak', 'Queda em relação ao pico anterior'));

    var lastYear = null;
    cv.dates.forEach(function (d, i) {
      var yr = d.slice(0, 4);
      if (yr === lastYear) return;
      lastYear = yr;
      if (i === 0 && +d.slice(5, 7) > 2) return;
      svg('line', { x1: x(i), x2: x(i), y1: botB, y2: botB + 4, class: 'axis' }, c.svg);
      svg('text', { x: x(i), y: botB + 17, class: 'tick', 'text-anchor': i === 0 ? 'start' : 'middle' }, c.svg, yr);
    });
    hover(c, L, c.w - R, topA, botB, n, xi, function (i) {
      return '<b>' + fmtDate(cv.dates[i]) + '</b>' + tr('Portfolio ', 'Carteira ') + num(cv.strategy[i], 1) + '<br>' +
        tr('Drawdown ', 'Queda ') + num(cv.drawdown[i], 1).replace('-', '−') + '%<br>' + tr('Open pairs ', 'Pares abertos ') + cv.open_pairs[i];
    });
  }

  /* 5. distribution of trade returns */
  function drawHist() {
    var c = start('fig-hist', 210);
    if (!c) return;
    var rets = D.trades.map(function (t) { return t.ret * 100; });
    var step = 2, lo = Math.floor(Math.min.apply(null, rets) / step) * step, hi = Math.ceil(Math.max.apply(null, rets) / step) * step;
    lo = Math.max(lo, -30); hi = Math.min(hi, 30);
    var bins = [], k;
    for (k = lo; k < hi; k += step) bins.push({ a: k, n: 0 });
    rets.forEach(function (v) {
      var i = Math.floor((Math.max(lo, Math.min(hi - 1e-9, v)) - lo) / step);
      bins[i].n++;
    });
    var L = 34, R = 8, top = 12, bottom = 172, max = Math.max.apply(null, bins.map(function (b) { return b.n; }));
    var x = scale(lo, hi, L, c.w - R), y = scale(0, max, bottom, top);
    niceTicks(0, max, 3).forEach(function (v) {
      if (v === 0) return;
      svg('line', { x1: L, x2: c.w - R, y1: y(v), y2: y(v), class: 'grid' }, c.svg);
      svg('text', { x: L - 6, y: y(v) + 4, class: 'tick', 'text-anchor': 'end' }, c.svg, v);
    });
    bins.forEach(function (b) {
      if (!b.n) return;
      svg('rect', { x: x(b.a) + 1, y: y(b.n), width: Math.max(1, x(b.a + step) - x(b.a) - 2), height: bottom - y(b.n), class: b.a < 0 ? 'bar accent' : 'bar' }, c.svg);
    });
    svg('line', { x1: L, x2: c.w - R, y1: bottom, y2: bottom, class: 'axis' }, c.svg);
    var every = (hi - lo) / step > 16 && c.narrow ? 8 : 4;
    for (k = Math.ceil(lo / every) * every; k <= hi; k += every) {
      svg('text', { x: x(k), y: bottom + 16, class: 'tick', 'text-anchor': 'middle' }, c.svg, (k > 0 ? '+' : k < 0 ? '−' : '') + Math.abs(k) + '%');
    }
    svg('text', { x: (L + c.w - R) / 2, y: bottom + 34, class: 'cap', 'text-anchor': 'middle' }, c.svg,
      c.narrow ? tr('Return per trade', 'Retorno por operação') : tr('Return per trade, on the capital given to the pair', 'Retorno por operação, sobre o capital dado ao par'));
  }

  /* 6. same engine with and without look-ahead in the selection */
  function drawLookahead() {
    var c = start('fig-lookahead', 260);
    if (!c) return;
    var cv = D.curve, n = cv.dates.length, L = 34, R = c.narrow ? 84 : 118;
    var x = scale(0, n - 1, L, c.w - R), idx = cv.dates.map(function (_, i) { return x(i); });
    var all = cv.strategy.concat(cv.lookahead, [100]);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all), pad = (hi - lo) * 0.06, top = 12, bottom = 226;
    var y = scale(lo - pad, hi + pad, bottom, top);
    niceTicks(lo, hi, 4).forEach(function (v) {
      svg('line', { x1: L, x2: c.w - R, y1: y(v), y2: y(v), class: v === 100 ? 'axis' : 'grid' }, c.svg);
      svg('text', { x: L - 6, y: y(v) + 4, class: 'tick', 'text-anchor': 'end' }, c.svg, v);
    });
    svg('path', { d: path(idx, cv.lookahead.map(y)), class: 'line accent' }, c.svg);
    svg('path', { d: path(idx, cv.strategy.map(y)), class: 'line' }, c.svg);
    var y1 = y(cv.lookahead[n - 1]), y2 = y(cv.strategy[n - 1]);
    if (Math.abs(y1 - y2) < 30) { var s = y1 < y2 ? -1 : 1; var m = (y1 + y2) / 2; y1 = m + s * 15; y2 = m - s * 15; }
    var a = tr(['Pairs chosen', 'with future data'], ['Pares escolhidos', 'com dados futuros']);
    var b = tr(['Pairs chosen', 'with past data'], ['Pares escolhidos', 'só com o passado']);
    [[a, y1, 'label accent'], [b, y2, 'label']].forEach(function (g) {
      svg('text', { x: c.w - R + 6, y: g[1] - 2, class: g[2] }, c.svg, g[0][0]);
      svg('text', { x: c.w - R + 6, y: g[1] + 11, class: g[2] }, c.svg, g[0][1]);
    });
    var lastYear = null;
    cv.dates.forEach(function (d, i) {
      var yr = d.slice(0, 4);
      if (yr === lastYear) return;
      lastYear = yr;
      svg('text', { x: x(i), y: bottom + 17, class: 'tick', 'text-anchor': i === 0 ? 'start' : 'middle' }, c.svg, yr);
    });
  }

  /* numbers written into the text */
  function fill() {
    var m = D.metrics, la = D.metrics_lookahead, bv = D.metrics_bova11, W = D.windows;
    var mean = function (key) { return W.reduce(function (a, w) { return a + w.funnel[key]; }, 0) / W.length; };
    var values = {
      'annual': pct(m.annual_return, 1, true), 'total': pct(m.total_return, 1, true), 'vol': pct(m.annual_volatility, 1),
      'sharpe': num(m.sharpe, 2).replace('-', '−'), 'mdd': pct(m.max_drawdown, 1), 'trades': num(m.trades, 0),
      'win': pct(m.win_rate, 0), 'avgtrade': pct(m.avg_trade_return, 2, true), 'days': num(m.median_days, 0),
      'corr': num(m.correlation_benchmark, 2).replace('-', '−'), 'gross': pct(m.avg_gross_exposure, 0),
      'open': num(Math.round(m.avg_open_pairs), 0), 'rev-ret': pct(m.avg_reversion_return || 0, 1, true),
      'end-ret': pct(Math.abs(m.avg_window_end_return || 0), 1), 'distinct': m.distinct_pairs, 'pf': num(m.profit_factor, 2), 'reversion': pct(m.reversion_share, 0),
      'la-annual': pct(la.annual_return, 1, true), 'la-total': pct(la.total_return, 1, true), 'la-sharpe': num(la.sharpe, 2).replace('-', '−'),
      'bova-annual': pct(bv.annual_return, 1, true), 'bova-vol': pct(bv.annual_volatility, 1), 'bova-mdd': pct(bv.max_drawdown, 1),
      'windows': W.length, 'tested': num(W[0].funnel.tested, 0), 'coint': num(Math.round(mean('cointegrated')), 0),
      'selected': num(Math.round(mean('selected')), 0), 'stocks': W[0].funnel.stocks, 'tickers': num(D.period.tickers, 0),
      'splits': num(D.period.split_adjustments, 0), 'pair-a': D.example.a, 'pair-b': D.example.b,
      'trade-start': fmtDate(D.period.trade_start), 'trade-end': fmtDate(D.period.trade_end),
      'entry': num(D.config.entry_z, 1), 'exit': num(D.config.exit_z, 1),
      'cost': pct(D.config.transaction_cost + D.config.slippage, 2), 'pairs': D.config.n_pairs
    };
    document.querySelectorAll('[data-v]').forEach(function (el) {
      var v = values[el.getAttribute('data-v')];
      if (v != null) el.textContent = v;
    });

    var ty = document.getElementById('table-yearly');
    if (ty) {
      ty.innerHTML = '<thead><tr><th></th>' + D.yearly.map(function (r) { return '<th>' + r.year + '</th>'; }).join('') + '</tr></thead><tbody>' +
        '<tr><th>' + tr('Strategy', 'Estratégia') + '</th>' + D.yearly.map(function (r) { return '<td>' + pct(r.strategy, 1, true) + '</td>'; }).join('') + '</tr>' +
        '<tr class="dim"><th>BOVA11</th>' + D.yearly.map(function (r) { return '<td>' + pct(r.bova11, 1, true) + '</td>'; }).join('') + '</tr></tbody>';
    }
    var tp = document.getElementById('table-pairs');
    if (tp) {
      var rows = D.pairs.slice(0, 5).concat(D.pairs.slice(-5));
      tp.innerHTML = '<thead><tr><th>' + tr('Pair', 'Par') + '</th><th>' + tr('Trades', 'Operações') + '</th><th>' + tr('Won', 'Ganhas') +
        '</th><th>' + tr('Avg. days', 'Dias, média') + '</th><th>' + tr('Result', 'Resultado') + '</th></tr></thead><tbody>' +
        rows.map(function (p, i) {
          return (i === 5 ? '<tr class="gap"><td colspan="5">' + tr('…and the five worst', '…e os cinco piores') + '</td></tr>' : '') +
            '<tr><th>' + p.pair.replace('-', ' / ') + '</th><td>' + p.trades + '</td><td>' + pct(p.win, 0) + '</td><td>' + num(p.days, 0) +
            '</td><td>' + (p.pnl_pct < 0 ? '−' : '+') + num(Math.abs(p.pnl_pct), 2) + ' pp</td></tr>';
        }).join('') + '</tbody>';
    }
  }

  function render() {
    fill();
    drawExample(); drawFunnel(); drawWindows(); drawEquity(); drawHist(); drawLookahead();
  }

  /* language and theme share the keys used by the portfolio site */
  var langBtn = document.querySelector('.lang-toggle');
  function setLang(l, save) {
    body.setAttribute('data-lang', l);
    root.lang = l === 'pt' ? 'pt-BR' : 'en';
    langBtn.textContent = l === 'pt' ? 'EN' : 'PT';
    if (save) { try { localStorage.setItem('lang', l); } catch (e) {} }
    render();
  }
  langBtn.addEventListener('click', function () { setLang(lang() === 'pt' ? 'en' : 'pt', true); });
  document.querySelector('.theme').addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
  });
  var saved = null;
  try { saved = localStorage.getItem('lang'); } catch (e) {}
  setLang(saved === 'pt' ? 'pt' : 'en', false);

  var timer, lastW = window.innerWidth;
  window.addEventListener('resize', function () {
    if (window.innerWidth === lastW) return;
    lastW = window.innerWidth;
    clearTimeout(timer);
    timer = setTimeout(render, 150);
  });
})();
