"""Pinned review of audio-album editing components."""

FILES = {
    'dialogs/AddAudioFileDialog.vue': (69,128,'handleConfirmAdd','Adds an audio file to the album.'),
    'dialogs/AddSingleKeyEffectSubDialog.vue': (51,432,'handleConfirm','Associates a sound effect with one key.'),
    'dialogs/CreateKeySoundDialog.vue': (55,405,'handleSave','Saves a new key sound.'),
    'dialogs/CreateSoundDialog.vue': (58,253,'handlePreview','Creates and previews a sound.'),
    'dialogs/EditKeySoundDialog.vue': (78,539,'handleSave','Updates or deletes a key sound.'),
    'dialogs/EditSingleKeyEffectSubDialog.vue': (45,374,'doSave','Updates an effect associated with one key.'),
    'dialogs/EditSoundDialog.vue': (64,356,'handlePreview','Previews and updates a saved sound.'),
    'dialogs/EveryKeyEffectDialog.vue': (61,346,'handleConfirm','Configures a sound effect for every key.'),
    'dialogs/ManageAudioFilesDialog.vue': (64,174,'handleDelete','Manages selection and deletion of audio files.'),
    'dialogs/SingleKeyEffectDialog.vue': (69,177,'handleEditKey','Opens the editor for a key effect.'),
    'steps/StepCraftKeySounds.vue': (65,178,'handleEditKeySound','Opens the key sound editor from the wizard.'),
    'steps/StepDefineSounds.vue': (66,179,'handleEditSound','Opens the sound editor from the wizard.'),
    'steps/StepLinkageEffects.vue': (67,218,'handleStepClick','Handles interaction with the linkage wizard step.'),
    'steps/StepLoadAudioFiles.vue': (64,135,'handleManageFiles','Opens the file manager from the wizard.'),
}

NEGATIVE_FILES = {
    ('LuSrackhall/KeyTone',117,f'frontend/src/components/keytone-album/{path}'):
        (0,reason,((template_line,'<template>'),(handler_line,f'function {handler}(')))
    for path,(template_line,handler_line,handler,reason) in FILES.items()
}
