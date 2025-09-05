[app]
title = UltimateBudget
package.name = ultimatebudget
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,csv,pdf
version = 1.0
orientation = portrait
fullscreen = 0
requirements = python3,kivy,fpdf2,matplotlib,kivy_garden.matplotlib
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET

[buildozer]
log_level = 2
warn_on_root = 1
android.accept_sdk_license = True
