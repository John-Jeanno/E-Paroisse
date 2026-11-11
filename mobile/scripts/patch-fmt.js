#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Patch fmt constexpr errors by replacing FMT_STRING with non-constexpr version
const fmtPath = path.join(__dirname, '../ios/Pods/fmt/include/fmt/format-inl.h');

if (!fs.existsSync(fmtPath)) {
    console.log('ℹ️  fmt/format-inl.h not found yet (normal during npm install)');
    process.exit(0);
}

try {
    let content = fs.readFileSync(fmtPath, 'utf8');

    // Replace FMT_STRING with fmt::string_view to avoid constexpr issues
    // This is a workaround for Xcode C++20 constexpr compatibility
    const originalCount = (content.match(/FMT_STRING/g) || []).length;

    if (originalCount === 0) {
        console.log('✅ fmt already patched or FMT_STRING not found');
        process.exit(0);
    }

    content = content.replace(/FMT_STRING\("([^"]*)"\)/g, 'fmt::string_view("$1")');

    fs.writeFileSync(fmtPath, content, 'utf8');
    console.log(`✅ Patched fmt: replaced ${originalCount} FMT_STRING instances`);
} catch (err) {
    console.warn('⚠️  Could not patch fmt:', err.message);
    // Don't fail, might not be ready yet
    process.exit(0);
}
