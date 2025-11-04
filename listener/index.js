// import makeWASocket, { useMultiFileAuthState, DisconnectReason, downloadMediaMessage } from '@whiskeysockets/baileys'
// import axios from 'axios'
// import qrcode from 'qrcode'
// import fs from 'fs'
// import pino from 'pino';


// const API_URL = 'http://fastapi:8000/webhook'

// async function startBot() {
//     const { state, saveCreds } = await useMultiFileAuthState('auth')
//     // Configure logger
//     const logger = pino({ level: 'info' });
//     const sock = makeWASocket({
//         auth: state,
//         printQRInTerminal: false,
//         logger: logger,
//         connectTimeoutMs: 60000, // Increase timeout to 60 seconds
//         defaultQueryTimeoutMs: 60000,
//         retryRequestDelayMs: 1000
//     })

//     sock.ev.on('creds.update', saveCreds)

//     sock.ev.on('connection.update', async (update) => {
//         const { connection, lastDisconnect, qr } = update

//         if (qr) {
//             console.log('📸 QR code detected, saving as qr.png...')
//             try {
//                 const qrDir = '/app/qr'
//                 fs.mkdirSync(qrDir, { recursive: true })
//                 await qrcode.toFile(`${qrDir}/qr.png`, qr)
//                 console.log('✅ QR code saved successfully')
//             } catch (err) {
//                 console.error('❌ Failed to save QR code:', err.message)
//             }
//         }

//         if (connection === 'close') {
//             const statusCode = lastDisconnect?.error?.output?.statusCode
//             const shouldReconnect = statusCode !== DisconnectReason.loggedOut
//             console.log('⚠️ Connection closed due to:', lastDisconnect?.error?.message)

//             if (shouldReconnect) {
//                 console.log('🔄 Reconnecting...')
//                 setTimeout(startBot, 5000) // Wait 5 seconds before reconnecting
//             }
//         } else if (connection === 'connecting') {
//             console.log('🔄 Connecting to WhatsApp...')
//         } else if (connection === 'open') {
//             console.log('✅ Connected to WhatsApp successfully!')
//         }
//     })

//     sock.ev.on('messages.upsert', async (msg) => {
//         try {
//             const message = msg.messages[0]
//             if (!message?.message) return

//             const from = message.key.remoteJid
//             const hasImage = !!message.message.imageMessage
//             const messageTimestamp = message.messageTimestamp?.low || message.messageTimestamp
//             const sentAt = new Date(Number(messageTimestamp) * 1000).toISOString()
//             let groupName = null
//             if (from.endsWith('@g.us')) {
//                 const groupMetadata = await sock.groupMetadata(from)
//                 groupName = groupMetadata.subject
//                 console.log(`📢 Message received in group: ${groupName}`)
//             }

//             if (hasImage) {
//                 console.log('📸 Image received from', from)
//                 try {
//                     const buffer = await downloadMediaMessage(
//                         message,
//                         'buffer',
//                         {},
//                         {
//                             logger: sock.logger,
//                             reuploadRequest: sock.updateMediaMessage
//                         }
//                     )
//                     const timestamp = new Date().getTime()
//                     const filename = `/app/incoming/${timestamp}_${message.key.id}.jpg`

//                     // Ensure directory exists and is writable
//                     if (!fs.existsSync('/app/incoming')) {
//                         fs.mkdirSync('/app/incoming', { recursive: true })
//                     }

//                     // Save the image with detailed error logging
//                     try {
//                         fs.writeFileSync(filename, buffer)
//                         console.log(`✅ Image saved successfully to ${filename}`)

//                         // Log file existence check
//                         if (fs.existsSync(filename)) {
//                             const stats = fs.statSync(filename)
//                             console.log(`File size: ${stats.size} bytes`)
//                         }
//                     } catch (writeError) {
//                         console.error('❌ Failed to write file:', writeError)
//                         console.error('Write location:', filename)
//                         console.error('Buffer size:', buffer.length)
//                     }

//                     // await axios.post(API_URL, {
//                     //     entry: [{
//                     //         changes: [{
//                     //             value: {
//                     //                 messages: [{
//                     //                     id: message.key.id,
//                     //                     from: from,
//                     //                     type: 'image',
//                     //                     image: { id: message.key.id },
//                     //                     timestamp: timestamp
//                     //                 }]
//                     //             }
//                     //         }]
//                     //     }]
//                     // })
//                     await axios.post(API_URL, {
//                         local_image_path: filename,
//                         image_filename: `${timestamp}_${message.key.id}.jpg`, // Path to the saved image
//                         sender_jid: from,          // The sender's JID
//                         message_id: message.key.id, // Optional, but good for tracking
//                         from_group: groupName || null,
//                         sent_at: sentAt
//                     });
//                 } catch (err) {
//                     console.error('❌ Failed to process image:', err.message)
//                     console.error('Message content:', JSON.stringify(message.message, null, 2))
//                 }
//             }
//         } catch (err) {
//             console.error('❌ Error processing message:', err.message)
//         }
//     })

//     // Handle errors globally
//     sock.ev.on('error', (err) => {
//         console.error('❌ Connection error:', err.message)
//     })
// }

// // Start the bot with error handling
// try {
//     startBot()
// } catch (err) {
//     console.error('❌ Failed to start bot:', err.message)
//     process.exit(1)
// }

import makeWASocket, { useMultiFileAuthState, DisconnectReason, downloadMediaMessage } from '@whiskeysockets/baileys'
import axios from 'axios'
import qrcode from 'qrcode'
import fs from 'fs'
import pino from 'pino';


const API_URL = process.env.API_URL || 'http://localhost:8000/webhook'

async function startBot() {
    const { state, saveCreds } = await useMultiFileAuthState('auth')
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
            console.log('📸 QR code detected, saving as qr.png...')
            try {
                const qrDir = '/app/qr'
                fs.mkdirSync(qrDir, { recursive: true })
                await qrcode.toFile(`${qrDir}/qr.png`, qr)
                console.log('✅ QR code saved successfully')
            } catch (err) {
                console.error('❌ Failed to save QR code:', err.message)
            }
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
            if (message.key.fromMe) {
                console.log('⏩ Skipping image I sent myself')
                return
            }

            const from = message.key.remoteJid
            const hasImage = !!message.message.imageMessage

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
                    groupName = 'Group Name Error'
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
                    const filename = `/app/incoming/${timestamp}_${message.key.id}.jpg`

                    // Ensure directory exists and is writable
                    if (!fs.existsSync('/app/incoming')) {
                        fs.mkdirSync('/app/incoming', { recursive: true })
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

                    // 3. Post to FastAPI webhook
                    await axios.post(API_URL, {
                        local_image_path: filename,
                        image_filename: `${timestamp}_${message.key.id}.jpg`,
                        sender_jid: senderJid, // Use the participant JID for sender
                        message_id: message.key.id,
                        group_name: groupName, // Pass the detected group name
                        sent_at: sentAt
                    });

                } catch (err) {
                    console.error('❌ Failed to process image:', err.message)
                    console.error('Message content:', JSON.stringify(message.message, null, 2))
                }
            } else if (hasImage) {
                console.log(`⚠️ Ignoring image from direct chat: ${from}`)
            }
            // --- END CRITICAL FIX ---

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