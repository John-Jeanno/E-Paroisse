const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '..', 'node_modules', 'expo-device', 'ios', 'UIDevice.swift');

if (!fs.existsSync(filePath)) {
    console.warn(`expo-device patch skipped: file not found at ${filePath}`);
    process.exit(0);
}

const content = fs.readFileSync(filePath, 'utf8');
const replacement = `  var isSimulator: Bool {
    #if targetEnvironment(simulator)
      return true
    #else
      return false
    #endif
  }`;

const blockPattern = /  var isSimulator: Bool \{[\s\S]*?\n\s*\}/m;

if (content.includes(replacement)) {
    console.log('expo-device UIDevice.swift already patched');
    process.exit(0);
}

if (!blockPattern.test(content)) {
    console.warn('expo-device UIDevice.swift did not contain an isSimulator property block; patch was not applied.');
    process.exit(0);
}

const patched = content.replace(blockPattern, replacement);
fs.writeFileSync(filePath, patched, 'utf8');
console.log('Patched expo-device UIDevice.swift');
