
// listener/index.js

import makeWASocket, { useMultiFileAuthState, DisconnectReason, downloadMediaMessage } from '@whiskeysockets/baileys'
import axios from 'axios'
import qrcode from 'qrcode'
import fs from 'fs'
import pino from 'pino';

// const processedMessages = new Set();
const API_URL = process.env.API_URL || 'http://localhost:8000/webhook'
//"http://fastapi_app:8000/webhook"
//os.getev(API_URL)
//'http://localhost:8000/webhook'
// process.env.API_URL ||

async function startBot() {
    const authFolder = '/app/auth'
    // if (fs.existsSync(authFolder)) {
    //     fs.readdirSync(authFolder).forEach(file => {
    //         if (file.endsWith('.json')) { // session files end with .json
    //             fs.unlinkSync(`${authFolder}/${file}`);
    //         }
    //     });
    //     console.log('✅ Old session files cleared');
    // }
    const { state, saveCreds } = await useMultiFileAuthState(authFolder)
    // const { state, saveCreds } = await useMultiFileAuthState('auth')
    // Configure logger
    const logger = pino({ level: 'info' });
    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,
        logger: logger,
        connectTimeoutMs: 60000, // Increase timeout to 60 seconds
        defaultQueryTimeoutMs: 60000,
        retryRequestDelayMs: 1000
    })


    sock.ev.on('creds.update', saveCreds)

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update


        if (qr) {
            const qrDir = '/app/auth/qr';
            fs.mkdirSync(qrDir, { recursive: true });
            await qrcode.toFile(`${qrDir}/qr.png`, qr);

            // Log base64 for scanning
            const qrBase64 = await qrcode.toDataURL(qr);
            console.log('📸 QR Code (Base64):', qrBase64);
        }
        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut
            console.log('⚠️ Connection closed due to:', lastDisconnect?.error?.message)

            if (shouldReconnect) {
                console.log('🔄 Reconnecting...')
                setTimeout(startBot, 5000) // Wait 5 seconds before reconnecting
            }
        } else if (connection === 'connecting') {
            console.log('🔄 Connecting to WhatsApp...')
        } else if (connection === 'open') {
            console.log('✅ Connected to WhatsApp successfully!')
        }
    })

    sock.ev.on('messages.upsert', async (msg) => {
        try {
            const message = msg.messages[0]
            if (!message?.message) return
            // const messageId = message.key.id
            // // ✅ Skip if this message was already processed
            // if (processedMessages.has(messageId)) {
            //     console.log(`⚠️ Duplicate message ignored: ${messageId}`);
            //     return;
            // }

            // ✅ Mark this message as processed
            // processedMessages.add(messageId);
            if (message.key.fromMe) {
                console.log('⏩ Skipping image I sent myself')
                return
            }

            const from = message.key.remoteJid
            const hasImage = !!message.message.imageMessage
            const imageMessage = message.message.imageMessage;
            const imageUrl = imageMessage.url; // Extract image URL if needed
            const hasDocument = !!message.message.documentMessage
            const isPdf = hasDocument && message.message.documentMessage.mimetype === 'application/pdf';
            // In a group, the actual sender is in message.key.participant
            // If it's a direct chat (which we now ignore), participant will be null/undefined.
            const senderJid = message.key.participant || from;

            const messageTimestamp = message.messageTimestamp?.low || message.messageTimestamp
            const sentAt = new Date(Number(messageTimestamp) * 1000).toISOString()

            let groupName = null

            // --- CRITICAL FIX: ONLY PROCESS IF FROM A GROUP AND IS AN IMAGE ---
            if (from.endsWith('@g.us') && hasImage) {

                // 1. Get Group Name
                try {
                    const groupMetadata = await sock.groupMetadata(from)
                    groupName = groupMetadata.subject
                    console.log(`📢 Image received in group: ${groupName} from ${senderJid}`)
                } catch (groupError) {
                    console.error(`❌ Failed to get group metadata for ${from}: ${groupError.message}`)
                    groupName = 'Ini Transgestiona Ciudad'
                }

                // 2. Image Processing Block
                try {
                    const buffer = await downloadMediaMessage(
                        message,
                        'buffer',
                        {},
                        {
                            logger: sock.logger,
                            reuploadRequest: sock.updateMediaMessage
                        }
                    )
                    const timestamp = new Date().getTime()
                    const filename = `/app/auth/incoming/${timestamp}_${message.key.id}.jpg`

                    // Ensure directory exists and is writable
                    if (!fs.existsSync('/app/auth/incoming')) {
                        fs.mkdirSync('/app/auth/incoming', { recursive: true })
                    }

                    // Save the image
                    try {
                        fs.writeFileSync(filename, buffer)
                        console.log(`✅ Image saved successfully to ${filename}`)

                        if (fs.existsSync(filename)) {
                            const stats = fs.statSync(filename)
                            console.log(`File size: ${stats.size} bytes`)
                        }
                    } catch (writeError) {
                        console.error('❌ Failed to write file:', writeError)
                        console.error('Write location:', filename)
                        console.error('Buffer size:', buffer.length)
                        return // Stop processing if file write fails
                    }
                    const imageBase64 = fs.readFileSync(filename, { encoding: 'base64' });

                    // Send Base64 to FastAPI
                    await axios.post(API_URL, {
                        image_base64: imageBase64,
                        image_filename: `${timestamp}_${message.key.id}.jpg`,
                        sender_jid: senderJid,
                        message_id: message.key.id,
                        group_name: groupName,
                        sent_at: sentAt
                    });

                    // // 3. Post to FastAPI webhook
                    // await axios.post(API_URL, {
                    //     local_image_path: filename,
                    //     image_filename: `${timestamp}_${message.key.id}.jpg`,
                    //     sender_jid: senderJid, // Use the participant JID for sender
                    //     message_id: message.key.id,
                    //     group_name: groupName, // Pass the detected group name
                    //     sent_at: sentAt,
                    //     image_url: imageUrl
                    // });

                } catch (err) {
                    console.error('❌ Failed to process image:', err.message)
                    console.error('Message content:', JSON.stringify(message.message, null, 2))
                }
            } else if (hasImage) {
                console.log(`⚠️ Ignoring image from direct chat: ${from}`)
            }
            //new addition for pdf
            if (from.endsWith('@g.us') && isPdf) {
                console.log(`📄 PDF document received in group: ${groupName}. Skipping OCR.`)

                // Send a minimal payload to the backend to signal insertion of an empty row
                await axios.post(API_URL, {
                    // Flag to tell the Python backend to insert an empty row
                    skip_ocr: true,
                    file_type: 'PDF',
                    sender_jid: senderJid,
                    message_id: message.key.id,
                    group_name: groupName,
                    sent_at: sentAt
                });
                console.log(`✅ Sent 'skip_ocr' signal to FastAPI for PDF.`)
            }
            //new addition for pdf


        } catch (err) {
            console.error('❌ Error processing message:', err.message)
        }
    })

    // Handle errors globally
    sock.ev.on('error', (err) => {
        console.error('❌ Connection error:', err.message)
    })
}

// Start the bot with error handling
try {
    startBot()
} catch (err) {
    console.error('❌ Failed to start bot:', err.message)
    process.exit(1)
}