async function auth_token_hash(r) {
    const auth = r.headersIn['authorization'];
    const nexus = r.headersIn['nexus-token'];
    let token = auth || nexus;
    let hash = token ? await crypto.subtle.digest('SHA-512', token) : await '';
    r.setReturnValue(Buffer.from(hash).toString('hex'));
}

export default {auth_token_hash};
