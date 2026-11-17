(() => {
  const block = document.querySelector('[data-download-os]');
  const linux = block?.querySelector('.first-page__download-button--linux');
  if (!linux) return;
  const ua = navigator.userAgent;
  const platform = navigator.userAgentData?.platform || navigator.platform || '';
  const isLinux = /linux/i.test(platform) && !/android/i.test(ua);
  block.dataset.downloadOs = isLinux ? 'linux' : 'macos';
  // Move the preferred download first for keyboard and screen reader order too.
  if (isLinux) block.prepend(linux);
  const setArchitecture = (architecture) => {
    const arch = /arm|aarch64/i.test(architecture) ? 'arm64' : 'amd64';
    linux.href = `/download/linux?arch=${arch}`;
    linux.querySelector('.download-button__size')?.remove();
    const size = linux.dataset[`${arch}Size`];
    if (size) {
      const label = document.createElement('span');
      label.className = 'download-button__size';
      label.textContent = size;
      linux.append(label);
    }
  };
  setArchitecture(`${platform} ${ua}`);
  if (isLinux && navigator.userAgentData?.getHighEntropyValues) {
    navigator.userAgentData.getHighEntropyValues(['architecture'])
      .then(({ architecture }) => { if (architecture) setArchitecture(architecture); })
      .catch(() => {});
  }
})();
