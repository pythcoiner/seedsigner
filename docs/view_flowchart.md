### ScanView
```mermaid
flowchart TB
    classDef add fill:#00ff7f,stroke:#000000,stroke-width:4px;
    
    
    A[ScanView] --> T1{decoder.is_seed}
    T1 -- False --> T2{decoder.is_psbt}
    T2 -- False --> T3{decoder.is_settings}
    T3 -- False --> T4{decoder.is_descriptor}
    T4 -- False --> T5{decoder.is_address}
    T5 -- True --> V50[AddressVerificationStartView]
    T5 -- False --> V99[NotYetImplementedView]
    
    T1 -- True --> T10{passphrase_required}
    T10 -- True --> V10[SeedAddPassphraseView]
    T10 -- False --> V11[SeedFinalizeView]
    
    T3 -- True --> V30[SettingsUpdatedView]
    V30 -- any_other_button ---> V32[MainMenuView]
    V30 -- back ---> V31[BackStackView]

    
    T4 -- True --> T40{descriptor.is_basic_multisig}
    T40 -- False --> V99[NotYetImplementedView]
    T40 -- True --> V42[MultisigWalletDescriptorView]
    
    T2 -- True --> V20[PSBTSelectSeedView]
    subgraph PSBT

    V20 -- back --> V210
    V20 -- "choose seed" --> V21[PSBTOverviewView]
    V20 -- "12 words" --> V22[SeedMnemonicEntryView]
    V20 -- "24 words" --> V22[SeedMnemonicEntryView]
    V20 -- "scan seed" --> AA[ScanView]
    
    V21 -- back --> V210[BackStackView]
    V21 -- psbt_parser.policy == None ----> V211[PSBTUnsupportedScriptTypeWarningView]
    V21 -- psbt_parser.change_amount == 0 ----> V212[PSBTNoChangeWarningView]
    end

    


    

```






































### test