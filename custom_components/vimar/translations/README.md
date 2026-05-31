# 🌍 Vimar Integration Translations

This directory contains translations for the Vimar By-Me integration config flow, options flow, and reauth flow.

## Available Languages

| Language | Code | Status | Completeness | Native Check |
|----------|------|--------|--------------|-------------|
| 🇬🇧 English | `en` | ✅ Complete | 100% | ✅ Native |
| 🇮🇹 Italian | `it` | ✅ Complete | 100% | ✅ Native |
| 🇩🇪 German | `de` | ✅ Complete | 100% | ⚠️ Review recommended |
| 🇫🇷 French | `fr` | ✅ Complete | 100% | ⚠️ Review recommended |
| 🇪🇸 Spanish | `es` | ✅ Complete | 100% | ⚠️ Review recommended |
| 🇳🇱 Dutch | `nl` | ✅ Complete | 100% | ⚠️ Review recommended |
| 🇵🇹 Portuguese | `pt` | ✅ Complete | 100% | ⚠️ Review recommended |

## Translation Coverage

All languages include complete translations for:

- ✅ **Config Flow** - Initial setup
  - User step (connection configuration)
  - Reauth confirmation step
  - All field labels and descriptions
  
- ✅ **Options Flow** - Configuration management
  - Connection settings (step 1)
  - Integration settings (step 2)
  - Advanced options (step 3)
  
- ✅ **Error Messages**
  - `invalid_auth` - Invalid credentials
  - `cannot_connect` - Connection failures
  - `invalid_cert` - SSL certificate errors
  - `save_cert_failed` - Certificate save errors
  - `unknown` - Unexpected errors
  - `regex_not_valid` - Invalid regex patterns
  
- ✅ **Abort Reasons**
  - `already_configured` - Duplicate configuration
  - `reauth_successful` - Successful re-authentication
  - `reauth_failed` - Failed re-authentication
  - `single_instance_allowed` - Multiple instances not allowed

## File Structure

Each translation file follows the standard Home Assistant translation format:

```json
{
  "config": {
    "step": { ... },
    "error": { ... },
    "abort": { ... }
  },
  "options": {
    "step": { ... },
    "error": { ... }
  }
}
```

## Contributing Translations

### Adding a New Language

1. Copy `en.json` as a template
2. Rename to the appropriate language code (e.g., `pl.json` for Polish)
3. Translate all strings to your language
4. Keep formatting placeholders intact (e.g., `{host}`)
5. Submit a Pull Request

### Improving Existing Translations

Native speakers are welcome to review and improve existing translations, especially for:
- 🇩🇪 German
- 🇫🇷 French  
- 🇪🇸 Spanish
- 🇳🇱 Dutch
- 🇵🇹 Portuguese

### Translation Guidelines

1. **Be User-Friendly**: Use clear, simple language
2. **Be Consistent**: Use the same terms throughout
3. **Be Concise**: Keep descriptions short and helpful
4. **Preserve Placeholders**: Keep `{variable}` placeholders unchanged
5. **Technical Terms**: Some terms (HTTPS, SSL, regex) can remain in English if commonly used
6. **Test Your Translations**: If possible, test in Home Assistant UI

### Example Translation

**English:**
```json
"description": "The credentials for {host} are no longer valid. Please enter your updated credentials."
```

**Italian:**
```json
"description": "Le credenziali per {host} non sono più valide. Inserisci le credenziali aggiornate."
```

**Key Points:**
- `{host}` placeholder preserved
- Natural language flow
- User-friendly tone

## Language Codes

Use [ISO 639-1 language codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes):

| Code | Language |
|------|----------|
| `en` | English |
| `it` | Italian |
| `de` | German |
| `fr` | French |
| `es` | Spanish |
| `nl` | Dutch |
| `pt` | Portuguese |
| `pl` | Polish |
| `cs` | Czech |
| `sv` | Swedish |
| `da` | Danish |
| `no` | Norwegian |
| `fi` | Finnish |
| `ru` | Russian |
| `zh-Hans` | Chinese (Simplified) |
| `ja` | Japanese |
| `ko` | Korean |

## Testing Translations

### Local Testing

1. Copy your translation file to `custom_components/vimar/translations/`
2. Restart Home Assistant
3. Change Home Assistant language to your translation
4. Test the integration config flow
5. Verify all strings appear correctly

### Validation

Before submitting:

1. ✅ Check JSON syntax is valid
2. ✅ Verify all keys from `en.json` are present
3. ✅ Confirm placeholders are preserved
4. ✅ Test in Home Assistant UI if possible

## Translation Status by Region

### 🇪🇺 Europe
- ✅ English (UK/Ireland)
- ✅ Italian (Italy - native market for Vimar)
- ✅ German (Germany/Austria/Switzerland)
- ✅ French (France/Belgium/Switzerland)
- ✅ Spanish (Spain)
- ✅ Dutch (Netherlands/Belgium)
- ✅ Portuguese (Portugal)
- ⏳ Polish - **NEEDED**
- ⏳ Czech - **NEEDED**
- ⏳ Swedish - **NEEDED**
- ⏳ Danish - **NEEDED**
- ⏳ Norwegian - **NEEDED**
- ⏳ Finnish - **NEEDED**

### 🌎 Americas  
- ✅ English (USA/Canada)
- ✅ Spanish (Latin America)
- ✅ Portuguese (Brazil)

### 🌏 Asia/Pacific
- ⏳ Chinese (Simplified) - **NEEDED**
- ⏳ Japanese - **NEEDED**
- ⏳ Korean - **NEEDED**

### 🌍 Other
- ⏳ Russian - **NEEDED**
- ⏳ Arabic - **NEEDED**

## Credits

### Translators

- 🇬🇧 **English**: [@WhiteWolf84](https://github.com/WhiteWolf84)
- 🇮🇹 **Italian**: [@WhiteWolf84](https://github.com/WhiteWolf84) (Native)
- 🇩🇪 **German**: Machine translation + review needed
- 🇫🇷 **French**: Machine translation + review needed
- 🇪🇸 **Spanish**: Machine translation + review needed
- 🇳🇱 **Dutch**: Machine translation + review needed
- 🇵🇹 **Portuguese**: Machine translation + review needed

**Want to be credited?** Submit a native speaker review or new translation!

## Resources

- [Home Assistant Translation Guidelines](https://developers.home-assistant.io/docs/internationalization/core/)
- [Translation File Format](https://developers.home-assistant.io/docs/internationalization/core/#translation-strings)
- [ISO 639-1 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)

## Questions?

Open an issue on GitHub or submit a Pull Request with your translation!

---

**Coverage**: 7 languages covering ~85% of European HA users 🎉

**Last Updated**: 2026-02-21
