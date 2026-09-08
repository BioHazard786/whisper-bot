# Privacy Policy for Psst! Whisper Bot

**Effective Date:** September 8, 2026  
**Last Updated:** September 8, 2026

This Privacy Policy explains how **Psst! Whisper Bot** ("Psst!", "the Bot", "we", "our") handles, processes, and protects your information when you interact with the bot across Telegram (via inline queries, direct messages, and group chats).

Privacy and confidentiality are the fundamental purposes of Psst! We are dedicated to ensuring that your messages remain strictly private, ephemeral, and accessible only to the recipients you designate.

---

## 1. Information We Process

To provide secure whisper messaging services, the Bot processes only the minimal data strictly necessary:

1. **Telegram User Data:**
   - **User ID & Username:** Required to verify your identity, validate recipient authorizations, and enforce access controls.
   - **First Name:** Used for display purposes on whisper announcements (e.g., indicating who sent the whisper).

2. **Whisper Message Content:**
   - The confidential text you choose to send through the Bot.

3. **Message Context Metadata:**
   - Temporary Telegram identifiers (e.g., inline message IDs, group chat IDs, callback query IDs) required to deliver responses and render interactive lock/unlock buttons.

We do **not** collect or store personal contact lists, phone numbers, location data, or payment information.

---

## 2. How Your Data Is Handled & Stored

Psst! is architected from the ground up around **strict data minimization and ephemerality**:

- **In-Memory Storage Only:** Whisper messages and recipient lists are held solely in volatile memory (RAM). They are **never written to persistent disk storage, databases, or external log files**.
- **One-Time Self-Destruction:** Whispers designated as "One-Time" (`is_one_time=True` or `!1`) are automatically and permanently destroyed the moment all intended recipients have opened them.
- **Automated TTL Eviction:** All active whispers are assigned a strict Time-to-Live (TTL) of 24 hours (or less). An automated background cleanup worker periodically purges all expired and destroyed whispers from memory.
- **Manual Deletion:** Senders retain the right to manually delete any active whisper before or after it has been read, which immediately purges it from the service.

---

## 3. Data Sharing & Third Parties

- **No Sale or Commercialization:** We do not sell, rent, monetize, or trade your personal data or message content to third parties, advertisers, or data brokers under any circumstances.
- **No Third-Party Analytics:** We do not use third-party analytics trackers, tracking pixels, or profiling services.
- **Telegram Platform Infrastructure:** All data transmissions occur across Telegram's Bot API infrastructure and are governed by [Telegram's Privacy Policy](https://telegram.org/privacy) and [Telegram Terms of Service](https://telegram.org/tos).

---

## 4. Security & Ephemeral Features

Psst! leverages the Telegram Bot API's newest privacy capabilities:

- **Ephemeral Commands (`is_ephemeral=True`):** In group chats supporting ephemeral commands, Telegram hides your `/whisper` input text from other group participants.
- **Ephemeral Message Delivery:** In groups, whisper content is delivered using Telegram's `ephemeral_message_parameters`, rendering the decrypted message only on the authorized recipient's chat timeline.
- **Private Fallback Modals:** In inline mode, whispers are displayed via secure Telegram alert modals (`answerCallbackQuery(show_alert=True)`), ensuring message text is never posted into the public chat log.

---

## 5. User Rights & Data Retention

Under applicable privacy regulations (including GDPR and CCPA):

- **Right to Erasure:** Because all messages are ephemeral and non-persistent, your data is erased automatically upon whisper destruction or expiration. You can also trigger immediate erasure at any time by clicking the "🗑️ Delete" button on your sent whispers.
- **Revocation:** You may stop using the Bot or remove it from your chats at any time.

---

## 6. Children's Privacy

Psst! is not directed toward children under the age of 13 (or the relevant age threshold in your jurisdiction), and we do not knowingly process data from children.

---

## 7. Changes to This Policy

We may update this Privacy Policy from time to time to reflect bot enhancements or regulatory changes. Any modifications will be posted to this document with an updated "Last Updated" date.

---

## 8. Contact & Operator Information

If you have questions, feedback, or concerns regarding this Privacy Policy or the security of Psst! Whisper Bot, please contact:

- **Developer / Maintainer:** Mohd Zaid
- **Email:** `mohdzaidmalik70@gmail.com`
- **GitHub Repository:** [BioHazard786/whisper-bot](https://github.com/BioHazard786/whisper-bot)
