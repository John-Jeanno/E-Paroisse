const fs = require('fs');
const path = require('path');

const filePath = path.join(
  __dirname,
  '..',
  'node_modules',
  'react-native-svg',
  'apple',
  'Elements',
  'RNSVGImage.mm'
);

const original = fs.readFileSync(filePath, 'utf8');
const oldRemoveObserver = `#if REACT_NATIVE_MINOR_VERSION > 84
    observerCoordinator.removeObserver(_imageResponseObserverProxy);
#else
    observerCoordinator.removeObserver(*_imageResponseObserverProxy);
#endif`;
const oldAddObserver = `#if REACT_NATIVE_MINOR_VERSION > 84
    observerCoordinator.addObserver(_imageResponseObserverProxy);
#else
    observerCoordinator.addObserver(*_imageResponseObserverProxy);
#endif`;

if (!original.includes('#if REACT_NATIVE_MINOR_VERSION > 84')) {
  if (
    original.includes('observerCoordinator.removeObserver(_imageResponseObserverProxy);') &&
    original.includes('observerCoordinator.addObserver(_imageResponseObserverProxy);')
  ) {
    process.exit(0);
  }
  throw new Error('Expected react-native-svg observer API was not found');
}

if (!original.includes(oldRemoveObserver) || !original.includes(oldAddObserver)) {
  throw new Error(
    'react-native-svg observer API changed; review and update scripts/patch-react-native-svg.js'
  );
}

const patched = original
  .replace(oldRemoveObserver, '    observerCoordinator.removeObserver(_imageResponseObserverProxy);')
  .replace(oldAddObserver, '    observerCoordinator.addObserver(_imageResponseObserverProxy);');

fs.writeFileSync(filePath, patched, 'utf8');
