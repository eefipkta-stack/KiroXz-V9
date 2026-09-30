package keystrokesmod.module.impl.hg;

import keystrokesmod.event.PreUpdateEvent;
import keystrokesmod.module.Module;
import keystrokesmod.module.ModuleManager;
import keystrokesmod.module.impl.other.SlotHandler;
import keystrokesmod.module.setting.impl.ButtonSetting;
import keystrokesmod.module.setting.impl.SliderSetting;
import keystrokesmod.utility.Utils;
import net.minecraft.client.gui.inventory.GuiInventory;
import net.minecraft.init.Items;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.Slot;
import net.minecraft.item.ItemStack;
import net.minecraft.network.play.client.C08PacketPlayerBlockPlacement;
import net.minecraft.network.play.client.C09PacketHeldItemChange;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;

public class AutoSoup extends Module {
    private final SliderSetting singleSoupHealth;
    private final SliderSetting doubleSoupHealth;
    private final SliderSetting betweenActionsDelay;
    private final SliderSetting afterSoupingDelay;
    private final ButtonSetting dropBowls;
    private final ButtonSetting breakBlocks;
    private final ButtonSetting cleanupBowls;

    private long lastSoupTime = 0;
    private long lastActionTime = 0;
    private int soupsToEat = 0;
    private int currentSoupSlot = -1;
    private int originalSlot = -1;
    private int step = 0; // 0=idle, 1=switch, 2=eat, 3=drop, 4=next/return
    
    // Para limpeza de bowls
    private long lastCleanupTime = 0;
    private static final long CLEANUP_INTERVAL = 500; // 500ms entre limpezas

    /**
     * Retorna true quando o AutoSoup deve PAUSAR:
     * - Item no cursor do inventário (segurando bowls, ingredientes, etc.)
     * - Recraft em andamento
     * - Crafting grid com itens
     * Assim que soltar o item / terminar recraft, volta a agir no mesmo tick.
     */
    private static boolean shouldPauseForInventory() {
        // Item no cursor do inventário (mc.thePlayer.inventory.getItemStack())
        // Isso funciona SEMPRE, com inventário aberto ou não
        ItemStack cursorStack = mc.thePlayer.inventory.getItemStack();
        if (cursorStack != null) {
            return true;
        }
        // Recraft em andamento
        if (ModuleManager.recraft != null && ModuleManager.recraft.isEnabled() && ModuleManager.recraft.isCrafting()) {
            return true;
        }
        // Crafting grid com algum item
        if (mc.currentScreen instanceof GuiInventory) {
            Container container = mc.thePlayer.inventoryContainer;
            for (int i = 1; i <= 4; i++) {
                if (container.getSlot(i).getHasStack()) {
                    return true;
                }
            }
        }
        return false;
    }

    public AutoSoup() {
        super("Auto Soup", category.hg, "Toma sopas automaticamente quando a vida cai");

        this.registerSetting(singleSoupHealth = new SliderSetting("Single soup", 7.0, 1.0, 9.5, 0.5, "❤"));
        this.registerSetting(doubleSoupHealth = new SliderSetting("Double soup", 4.0, 1.0, 9.5, 0.5, "❤"));
        this.registerSetting(betweenActionsDelay = new SliderSetting("Between actions", 0, 0, 150, 5, "ms"));
        this.registerSetting(afterSoupingDelay = new SliderSetting("After souping", 250, 250, 500, 10, "ms"));
        this.registerSetting(dropBowls = new ButtonSetting("Drop bowls", true));
        this.registerSetting(breakBlocks = new ButtonSetting("Break blocks", false));
        this.registerSetting(cleanupBowls = new ButtonSetting("Cleanup bowls", true));
    }

    @Override
    public void onDisable() {
        reset();
    }

    private void reset() {
        step = 0;
        soupsToEat = 0;
        currentSoupSlot = -1;
        originalSlot = -1;
        lastActionTime = 0;
    }

    public void forceStop() {
        reset();
    }

    @SubscribeEvent
    public void onPreUpdate(PreUpdateEvent event) {
        if (!Utils.nullCheck()) return;

        // Limpeza de bowls soltas no inventário (sempre roda)
        if (cleanupBowls.isToggled() && dropBowls.isToggled()) {
            cleanupSoloBowls();
        }

        // Pausa enquanto: inventário aberto E (segurando item no cursor OU recraft em andamento OU craftando)
        // Assim que soltar o item / terminar recraft / terminar craft, volta a agir no mesmo instante
        if (shouldPauseForInventory()) {
            if (step >= 1) {
                returnToOriginal();
            } else {
                reset();
            }
            return;
        }

        // Se está processando, continua
        if (step != 0) {
            processStep();
            return;
        }

        // Verifica cooldown
        if (System.currentTimeMillis() - lastSoupTime < afterSoupingDelay.getInput()) {
            return;
        }

        // Verifica vida (dividido por 2 para hearts)
        float health = mc.thePlayer.getHealth() / 2.0f;
        
        // Single soup: SEMPRE 1 sopa
        // Double soup: SEMPRE 2 sopas
        if (health <= doubleSoupHealth.getInput()) {
            soupsToEat = 2;
        } else if (health <= singleSoupHealth.getInput()) {
            soupsToEat = 1;
        } else {
            return;
        }
        
        // Salva slot original e encontra sopa
        originalSlot = mc.thePlayer.inventory.currentItem;
        currentSoupSlot = findSoupInHotbar();
        
        if (currentSoupSlot != -1) {
            step = 1; // Inicia: switch para sopa
            lastActionTime = System.currentTimeMillis();
        }
    }

    private void processStep() {
        if (shouldPauseForInventory()) {
            returnToOriginal();
            return;
        }

        long elapsed = System.currentTimeMillis() - lastActionTime;
        long delay = (long) betweenActionsDelay.getInput();
        
        // Aguarda delay entre ações
        if (elapsed < delay && step > 1) {
            return;
        }

        switch (step) {
            case 1: // SWITCH - Muda para slot da sopa
                if (currentSoupSlot == -1) {
                    returnToOriginal();
                    return;
                }

                // Verifica se tem sopa no slot
                ItemStack soupCheck = mc.thePlayer.inventory.getStackInSlot(currentSoupSlot);
                if (soupCheck == null || soupCheck.getItem() != Items.mushroom_stew) {
                    currentSoupSlot = findSoupInHotbar();
                    if (currentSoupSlot == -1) {
                        returnToOriginal();
                        return;
                    }
                }

                // Sincroniza client + server para o slot da sopa
                mc.getNetHandler().addToSendQueue(new C09PacketHeldItemChange(currentSoupSlot));
                if (!breakBlocks.isToggled()) {
                    mc.thePlayer.inventory.currentItem = currentSoupSlot;
                }

                step = 2;
                lastActionTime = System.currentTimeMillis();
                break;

            case 2: // EAT - Come a sopa (clique direito)
                // Re-sincroniza com o servidor antes de comer (jogador pode ter scrollado)
                mc.getNetHandler().addToSendQueue(new C09PacketHeldItemChange(currentSoupSlot));
                if (!breakBlocks.isToggled()) {
                    mc.thePlayer.inventory.currentItem = currentSoupSlot;
                }

                ItemStack soup = mc.thePlayer.inventory.getStackInSlot(currentSoupSlot);
                if (soup != null && soup.getItem() == Items.mushroom_stew) {
                    mc.getNetHandler().addToSendQueue(new C08PacketPlayerBlockPlacement(soup));

                    if (!breakBlocks.isToggled()) {
                        mc.thePlayer.inventory.decrStackSize(currentSoupSlot, 1);
                    }
                }

                step = 3;
                lastActionTime = System.currentTimeMillis();
                break;

            case 3: // DROP - Dropa a bowl via windowClick (slot exato, sem depender do held slot)
                if (dropBowls.isToggled()) {
                    dropBowlAtSlot(currentSoupSlot);
                }

                step = 4;
                lastActionTime = System.currentTimeMillis();
                break;

            case 4: // NEXT/RETURN
                soupsToEat--;

                if (soupsToEat > 0) {
                    int nextSoup = findSoupInHotbar();
                    if (nextSoup != -1) {
                        currentSoupSlot = nextSoup;
                        step = 1;
                        lastActionTime = System.currentTimeMillis();
                    } else {
                        returnToOriginal();
                    }
                } else {
                    returnToOriginal();
                }
                break;
        }
    }

    /**
     * Dropa a bowl em um slot específico.
     * Usa windowClick(mode=4) que dropa de um SLOT EXATO no container,
     * sem depender do slot selecionado no servidor (evita dropar espada/outros itens).
     */
    private void dropBowlAtSlot(int slot) {
        if (slot < 0 || slot > 8) return;

        Container container = mc.thePlayer.inventoryContainer;
        int containerSlot = 36 + slot;

        Slot invSlot = container.getSlot(containerSlot);
        if (!invSlot.getHasStack()) return;
        if (invSlot.getStack().getItem() != Items.bowl) return;
        if (invSlot.getStack().stackSize != 1) return;

        mc.playerController.windowClick(container.windowId, containerSlot, 0, 4, mc.thePlayer);
    }

    /**
     * Limpa bowls soltas APENAS na hotbar (9 slots principais)
     * Só dropa bowls com stackSize == 1
     * NÃO dropa bowls do inventário principal
     */
    private void cleanupSoloBowls() {
        // Não limpa durante processo de soup
        if (step != 0) return;
        // Não dropa bowls enquanto segura item no cursor ou está craftando
        if (shouldPauseForInventory()) return;
        
        // Cooldown para não spammar
        if (System.currentTimeMillis() - lastCleanupTime < CLEANUP_INTERVAL) {
            return;
        }
        
        Container container = mc.thePlayer.inventoryContainer;
        
        // APENAS hotbar (slots 36-44 no container = slots 0-8 do player)
        for (int i = 36; i <= 44; i++) {
            Slot slot = container.getSlot(i);
            if (slot.getHasStack()) {
                ItemStack stack = slot.getStack();
                // Só dropa se for bowl E stackSize == 1
                if (stack.getItem() == Items.bowl && stack.stackSize == 1) {
                    // Dropa usando windowClick (não muda slot)
                    mc.playerController.windowClick(container.windowId, i, 0, 4, mc.thePlayer);
                    lastCleanupTime = System.currentTimeMillis();
                    return; // Uma por vez
                }
            }
        }
    }

    /**
     * Volta para o slot original, sincronizando client e server.
     */
    private void returnToOriginal() {
        if (originalSlot != -1 && originalSlot >= 0 && originalSlot < 9) {
            mc.getNetHandler().addToSendQueue(new C09PacketHeldItemChange(originalSlot));
            mc.thePlayer.inventory.currentItem = originalSlot;
        }

        lastSoupTime = System.currentTimeMillis();
        reset();
    }

    /**
     * Encontra sopa na hotbar
     */
    private int findSoupInHotbar() {
        for (int i = 0; i < 9; i++) {
            // Pula slot atual se já usamos
            if (i == currentSoupSlot && step > 1) continue;
            
            ItemStack stack = mc.thePlayer.inventory.getStackInSlot(i);
            if (stack != null && stack.getItem() == Items.mushroom_stew) {
                return i;
            }
        }
        return -1;
    }

    @Override
    public String getPrettyInfo() {
        if (mc.thePlayer != null) {
            return String.format("%.1f❤", mc.thePlayer.getHealth() / 2.0f);
        }
        return "";
    }
}
