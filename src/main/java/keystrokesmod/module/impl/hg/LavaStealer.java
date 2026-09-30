package keystrokesmod.module.impl.hg;

import keystrokesmod.event.PreUpdateEvent;
import keystrokesmod.module.Module;
import keystrokesmod.module.setting.impl.ButtonSetting;
import keystrokesmod.module.setting.impl.ModeSetting;
import keystrokesmod.utility.Utils;
import net.minecraft.block.Block;
import net.minecraft.block.BlockLiquid;
import net.minecraft.block.material.Material;
import net.minecraft.client.entity.EntityPlayerSP;
import net.minecraft.init.Items;
import net.minecraft.item.ItemStack;
import net.minecraft.network.play.client.C08PacketPlayerBlockPlacement;
import net.minecraft.network.play.client.C09PacketHeldItemChange;
import net.minecraft.util.BlockPos;
import net.minecraft.util.MovingObjectPosition;
import net.minecraft.util.Vec3;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;

public class LavaStealer extends Module {
    private final ModeSetting mode;
    private final ButtonSetting debug;

    // Cooldown para evitar spam
    private long lastStealTime = 0;
    private static final long STEAL_COOLDOWN = 200L; // 200ms entre roubos

    public LavaStealer() {
        super("Lava Stealer", category.hg, "Rouba lava automaticamente");

        this.registerSetting(mode = new ModeSetting("Mode", new String[]{
                "Legit",    // Só funciona com balde na mão
                "Blatant"   // Troca para balde automaticamente
        }, 1));
        this.registerSetting(debug = new ButtonSetting("Debug", false));
    }

    @Override
    public void onEnable() {
        lastStealTime = 0;
    }

    @SubscribeEvent
    public void onPreUpdate(PreUpdateEvent event) {
        if (!Utils.nullCheck()) return;

        EntityPlayerSP player = mc.thePlayer;
        if (player == null || mc.theWorld == null) return;

        // Cooldown
        long now = System.currentTimeMillis();
        if (now - lastStealTime < STEAL_COOLDOWN) return;

        int modeIndex = (int) mode.getInput();

        // Verifica se tem lava source abaixo do jogador
        BlockPos lavaPos = findLavaBelow(player);
        if (lavaPos == null) return;

        if (modeIndex == 0) {
            // LEGIT: Só funciona se balde vazio estiver NA MÃO
            processLegitMode(player, lavaPos);
        } else {
            // BLATANT: Rouba independente, troca para balde se necessário
            processBlatantMode(player, lavaPos);
        }
    }

    /**
     * Encontra lava source abaixo do jogador
     */
    private BlockPos findLavaBelow(EntityPlayerSP player) {
        // Verifica diretamente abaixo do jogador
        int playerX = (int) Math.floor(player.posX);
        int playerZ = (int) Math.floor(player.posZ);
        int playerY = (int) Math.floor(player.posY);

        // Checa até 3 blocos abaixo
        for (int y = playerY; y >= playerY - 3; y--) {
            BlockPos pos = new BlockPos(playerX, y, playerZ);
            
            if (isLavaSource(pos)) {
                // Verifica se está dentro do alcance
                double dist = player.getDistanceSq(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5);
                if (dist <= 16.0) { // 4 blocos de alcance
                    return pos;
                }
            }
        }

        // Também checa blocos adjacentes (para pegar lava ao lado)
        for (int y = playerY - 1; y >= playerY - 2; y--) {
            for (int x = -1; x <= 1; x++) {
                for (int z = -1; z <= 1; z++) {
                    if (x == 0 && z == 0) continue;
                    
                    BlockPos pos = new BlockPos(playerX + x, y, playerZ + z);
                    if (isLavaSource(pos)) {
                        double dist = player.getDistanceSq(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5);
                        if (dist <= 16.0) {
                            return pos;
                        }
                    }
                }
            }
        }

        return null;
    }

    /**
     * Verifica se é lava source (metadata 0)
     */
    private boolean isLavaSource(BlockPos pos) {
        Block block = mc.theWorld.getBlockState(pos).getBlock();
        if (block.getMaterial() != Material.lava) return false;
        
        // Metadata 0 = source block
        int meta = block.getMetaFromState(mc.theWorld.getBlockState(pos));
        return meta == 0;
    }

    /**
     * LEGIT MODE: Só funciona com balde vazio NA MÃO
     * Rouba instantaneamente (0ms)
     */
    private void processLegitMode(EntityPlayerSP player, BlockPos lavaPos) {
        // Verifica se tem balde vazio na mão
        ItemStack heldItem = player.getHeldItem();
        if (heldItem == null || heldItem.getItem() != Items.bucket) {
            return; // Não tem balde na mão, não faz nada
        }

        // ROUBA INSTANTANEAMENTE!
        stealLava(player, lavaPos);
    }

    /**
     * BLATANT MODE: Rouba independente do slot
     * Troca automaticamente para o balde e rouba em 0ms
     */
    private void processBlatantMode(EntityPlayerSP player, BlockPos lavaPos) {
        // Primeiro, verifica se já tem balde na mão
        ItemStack heldItem = player.getHeldItem();
        if (heldItem != null && heldItem.getItem() == Items.bucket) {
            // Já tem balde na mão, rouba instantaneamente
            stealLava(player, lavaPos);
            return;
        }

        // Procura balde vazio na hotbar
        int bucketSlot = findEmptyBucketInHotbar();
        if (bucketSlot == -1) {
            // Procura no inventário e move para hotbar
            bucketSlot = moveEmptyBucketToHotbar();
            if (bucketSlot == -1) {
                if (debug.isToggled()) {
                    Utils.sendMessage("§c[LS] §7Sem balde vazio!");
                }
                return; // Sem balde
            }
        }

        // Salva slot atual
        int originalSlot = player.inventory.currentItem;

        // Troca para o balde via packet (server-side)
        mc.thePlayer.sendQueue.addToSendQueue(new C09PacketHeldItemChange(bucketSlot));
        
        // Atualiza client-side temporariamente
        player.inventory.currentItem = bucketSlot;

        // ROUBA INSTANTANEAMENTE!
        stealLava(player, lavaPos);

        // Volta para o slot original via packet
        mc.thePlayer.sendQueue.addToSendQueue(new C09PacketHeldItemChange(originalSlot));
        player.inventory.currentItem = originalSlot;
    }

    /**
     * Executa o roubo da lava (0ms delay)
     */
    private void stealLava(EntityPlayerSP player, BlockPos lavaPos) {
        // Envia packet de uso do item (clique direito)
        ItemStack bucket = player.getHeldItem();
        if (bucket == null || bucket.getItem() != Items.bucket) return;

        // Usa o balde na lava
        mc.playerController.sendUseItem(player, mc.theWorld, bucket);

        lastStealTime = System.currentTimeMillis();

        if (debug.isToggled()) {
            Utils.sendMessage("§a[LS] §fLava roubada em " + lavaPos.toString() + "!");
        }
    }

    /**
     * Encontra balde vazio na hotbar
     */
    private int findEmptyBucketInHotbar() {
        for (int i = 0; i < 9; i++) {
            ItemStack stack = mc.thePlayer.inventory.getStackInSlot(i);
            if (stack != null && stack.getItem() == Items.bucket) {
                return i;
            }
        }
        return -1;
    }

    /**
     * Move balde vazio do inventário para a hotbar
     */
    private int moveEmptyBucketToHotbar() {
        // Encontra um slot vazio na hotbar ou usa o slot 8
        int targetSlot = -1;
        for (int i = 0; i < 9; i++) {
            ItemStack stack = mc.thePlayer.inventory.getStackInSlot(i);
            if (stack == null) {
                targetSlot = i;
                break;
            }
        }
        if (targetSlot == -1) targetSlot = 8; // Último slot

        // Procura balde no inventário (slots 9-35)
        for (int i = 9; i < 36; i++) {
            ItemStack stack = mc.thePlayer.inventory.getStackInSlot(i);
            if (stack != null && stack.getItem() == Items.bucket) {
                // Move para hotbar usando swap (tecla de número)
                mc.playerController.windowClick(
                        mc.thePlayer.inventoryContainer.windowId,
                        i, targetSlot, 2, mc.thePlayer // 2 = swap
                );
                return targetSlot;
            }
        }
        return -1;
    }

    @Override
    public String getPrettyInfo() {
        String[] modes = {"Legit", "Blatant"};
        int index = (int) mode.getInput();
        return index >= 0 && index < modes.length ? modes[index] : "";
    }
}
