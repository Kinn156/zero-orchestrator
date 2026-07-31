// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use tauri_plugin_store::{StoreBuilder, StoreExt};

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
async fn save_key(app: tauri::AppHandle, key_name: String, key_value: String) -> Result<(), String> {
    let store = StoreBuilder::new(app.clone(), "keys.json").build();
    
    store.set(key_name.clone(), key_value).map_err(|e| e.to_string())?;
    store.save().map_err(|e| e.to_string())?;
    
    Ok(())
}

#[tauri::command]
async fn get_key(app: tauri::AppHandle, key_name: String) -> Result<Option<String>, String> {
    let store = StoreBuilder::new(app.clone(), "keys.json").build();
    
    let value = store.get(key_name).map_err(|e| e.to_string())?;
    
    Ok(value)
}

#[tauri::command]
async fn delete_key(app: tauri::AppHandle, key_name: String) -> Result<(), String> {
    let store = StoreBuilder::new(app.clone(), "keys.json").build();
    
    store.delete(key_name).map_err(|e| e.to_string())?;
    store.save().map_err(|e| e.to_string())?;
    
    Ok(())
}

#[tauri::command]
async fn list_keys(app: tauri::AppHandle) -> Result<Vec<String>, String> {
    let store = StoreBuilder::new(app.clone(), "keys.json").build();
    
    let keys: Vec<String> = store.keys().into_iter().collect();
    
    Ok(keys)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![greet, save_key, get_key, delete_key, list_keys])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
