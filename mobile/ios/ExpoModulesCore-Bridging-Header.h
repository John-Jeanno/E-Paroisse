//
//  ExpoModulesCore-Bridging-Header.h
//  EParoisse
//
//  Purpose: Provide React module visibility to ExpoModulesCore Swift code
//  This bridging header makes React/RCTView and other React types available
//  to Swift code in ExpoModulesCore that imports the React module.
//

#ifndef EXPOMODULESCORE_BRIDGING_HEADER_H
#define EXPOMODULESCORE_BRIDGING_HEADER_H

// Import React framework to make it visible to Swift
#import <React/RCTView.h>
#import <React/RCTComponent.h>
#import <React/RCTEventEmitter.h>
#import <React/RCTBridgeModule.h>
#import <React/RCTConvert.h>
#import <React/RCTDefines.h>
#import <React/RCTViewManager.h>
#import <React/RCTBridge.h>

// Also import common React dependencies used by ExpoModulesCore
#import <React/RCTUIManager.h>

#endif /* EXPOMODULESCORE_BRIDGING_HEADER_H */
