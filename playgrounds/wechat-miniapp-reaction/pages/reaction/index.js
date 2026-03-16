const BEST_KEY = 'reaction-best-ms';

Page({
  data: {
    state: 'idle',
    arenaText: '点击“开始测试”',
    arenaClass: '',
    current: '--',
    best: '--',
    buttonDisabled: false
  },

  onLoad() {
    const stored = wx.getStorageSync(BEST_KEY);
    const best = Number(stored);
    if (Number.isFinite(best) && best > 0) {
      this.setData({ best: `${best} ms` });
    }
  },

  onUnload() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  },

  setArena(text, className) {
    this.setData({
      arenaText: text,
      arenaClass: className || ''
    });
  },

  resetToIdle(text) {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.setData({
      state: 'idle',
      buttonDisabled: false,
      arenaText: text || '点击“开始测试”',
      arenaClass: ''
    });
  },

  startGame() {
    if (this.data.state !== 'idle') {
      return;
    }
    this.setData({
      state: 'waiting',
      current: '--',
      buttonDisabled: true
    });
    this.setArena('等待变绿后立即点击！', 'waiting');

    const delay = Math.floor(Math.random() * 3000) + 1500; // 1.5s - 4.5s
    this.timer = setTimeout(() => {
      this.setData({ state: 'ready' });
      this.startTime = Date.now();
      this.setArena('现在点击！', 'ready');
      this.timer = null;
    }, delay);
  },

  handleArenaTap() {
    const { state } = this.data;
    if (state === 'idle') {
      return;
    }

    if (state === 'waiting') {
      this.setArena('点早了！请重新开始', 'too-soon');
      this.resetToIdle('点早了！点击“开始测试”再来一次');
      return;
    }

    if (state === 'ready') {
      const reaction = Math.round(Date.now() - this.startTime);
      let best = Number(wx.getStorageSync(BEST_KEY));

      this.setData({ current: `${reaction} ms` });

      if (!Number.isFinite(best) || best <= 0 || reaction < best) {
        best = reaction;
        wx.setStorageSync(BEST_KEY, String(best));
        this.setData({ best: `${best} ms` });
      }

      this.resetToIdle(`你的反应时间：${reaction} ms（点击“开始测试”继续）`);
    }
  }
});
