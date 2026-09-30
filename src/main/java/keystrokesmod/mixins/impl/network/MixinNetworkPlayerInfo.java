package keystrokesmod.mixins.impl.network;

import keystrokesmod.module.ModuleManager;
import net.minecraft.client.network.NetworkPlayerInfo;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.IChatComponent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * NickBypass: altera o nick exibido na lista de jogadores (tab) para nicks mapeados.
 */
@Mixin(NetworkPlayerInfo.class)
public class MixinNetworkPlayerInfo {

    @Inject(method = "getDisplayName", at = @At("RETURN"), cancellable = true)
    private void onGetDisplayName(CallbackInfoReturnable<IChatComponent> cir) {
        // Removed forjamento logic
    }
}
