"""Pinned review of feature-scaffolding scripts and UI constants."""

BASH = '.specify/scripts/bash'
PS = '.specify/scripts/powershell'
SPEEDY = 'onlineeric/speedy-git-ext'
AL = 'FBakkensen/al-build-tools'
UNO = 'unoplatform/Uno.Themes'

NEGATIVE_FILES = {
    (SPEEDY,36,f'{BASH}/check-prerequisites.sh'):
        (0,'Checks for feature-planning inputs on disk.',((26,'REQUIRE_TASKS=false'),(188,'check_file "$TASKS"'))),
    (SPEEDY,36,f'{BASH}/common.sh'):
        (0,'Helpers resolve repository and template paths.',((5,'get_repo_root()'),(247,'[ -f "$core" ]'))),
    (SPEEDY,36,f'{BASH}/create-new-feature.sh'):
        (0,'Creates feature scaffolding and prints branch metadata.',((6,'SHORT_NAME='),(331,'FEATURE_NUM:'))),
    (SPEEDY,36,f'{BASH}/setup-plan.sh'):
        (0,'Sets up implementation plan and prints branch context.',((6,'JSON_MODE=false'),(70,'BRANCH:'))),
    (SPEEDY,36,f'{BASH}/update-agent-context.sh'):
        (0,'Generates agent context and emits example commands as text.',((261,'echo "cd src && pytest'),(807,'main "$@"'))),
    (AL,11,f'{PS}/check-task-prerequisites.ps1'):
        (0,'Checks presence of required planning artifacts.',((33,'Test-DirHasFiles -Path'),(34,'Test-FileExists -Path'))),
    (AL,11,f'{PS}/common.ps1'):
        (0,'Shared feature path and file-presence utilities.',((4,'function Get-RepoRoot'),(5,'git rev-parse'))),
    (AL,11,f'{PS}/create-new-feature.ps1'):
        (0,'Creates feature scaffolding and reports its specification path.',((50,'SPEC_FILE:'),(51,'FEATURE_NUM:'))),
    (AL,11,f'{PS}/get-feature-paths.ps1'):
        (0,'Reads and reports feature paths.',((13,'FEATURE_SPEC:'),(15,'TASKS:'))),
    (AL,11,f'{PS}/setup-plan.ps1'):
        (0,'Prepares the feature plan and reports its location and branch.',((19,'SPECS_DIR:'),(20,'BRANCH:'))),
    (AL,11,f'{PS}/update-agent-context.ps1'):
        (0,'Builds agent documentation and stores example commands as strings.',((41,'$commands ='),(91,'Usage: ./update-agent-context.ps1'))),
    (UNO,1622,f'{PS}/check-prerequisites.ps1'):
        (0,'Checks prerequisites for the specification workflow.',((17,'[CmdletBinding()]'),(146,'Test-FileExists -Path'))),
    (UNO,1622,f'{PS}/common.ps1'):
        (0,'Shared helpers resolve repository and feature paths.',((4,'function Get-RepoRoot'),(6,'git rev-parse'))),
    (UNO,1622,f'{PS}/create-new-feature.ps1'):
        (0,'Creates feature scaffolding and reports branch environment.',((280,'HAS_GIT:'),(281,'SPECIFY_FEATURE environment variable'))),
    (UNO,1622,f'{PS}/setup-plan.ps1'):
        (0,'Prepares a plan and reports current repository context.',((59,'BRANCH:'),(60,'HAS_GIT:'))),
    (UNO,1622,f'{PS}/update-agent-context.ps1'):
        (0,'Updates agent context and returns sample test commands as text.',((189,'return "cd src; pytest'),(447,'Agent context update completed'))),
    (UNO,1622,'src/library/Uno.Simple.WinUI/SimpleConstants.cs'):
        (0,'C# source declares a namespace and a static constants class.',((1,'namespace Uno.Simple'),(3,'internal static class SimpleConstants'))),
}
