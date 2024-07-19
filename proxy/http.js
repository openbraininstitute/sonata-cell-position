async function nexus_token_hash(r) {
    let token = r.headersIn['nexus-token'];
    let hash = token ? await crypto.subtle.digest('SHA-512', token) : await '';
    r.setReturnValue(Buffer.from(hash).toString('hex'));
}

export default {nexus_token_hash};
