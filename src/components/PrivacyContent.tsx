import { COMPANY_NAME, CONTACT_ADDRESS, CONTACT_EMAIL, ICP_NO, PRIVACY_EFFECTIVE_DATE, PRIVACY_VERSION } from '@/lib/agreement'

/**
 * 隐私政策正文（与 doc/隐私政策.md 同源，精简为前端可读版式）
 * 被 PrivacyPage 与 CalcPage 弹窗复用
 */
export default function PrivacyContent() {
  return (
    <article className="space-y-5 text-[13px] leading-relaxed text-fg-secondary">
      <header className="rounded-[12px] border border-border-gold bg-[#3a0a0a]/60 p-4">
        <h2 className="font-kai text-lg font-bold text-gold-light">振凡命理 · 隐私政策</h2>
        <div className="mt-2 space-y-1 text-xs text-muted">
          <p>生效日期：{PRIVACY_EFFECTIVE_DATE} · 版本：{PRIVACY_VERSION}</p>
          <p>运营主体：{COMPANY_NAME}</p>
          <p>备案号：{ICP_NO}</p>
        </div>
        <p className="mt-3 rounded-lg bg-gold/10 px-3 py-2 text-xs leading-relaxed text-gold-light">
          提示：您点击“开始推演/立即测算”即视为已阅读并同意本隐私政策全部内容。如您不同意，请勿提交信息。
        </p>
      </header>

      <section>
        <h3 className="mb-2 font-kai text-[15px] font-bold text-gold-light">一、我们如何收集和使用个人信息</h3>
        <p>仅在必要范围内收集以下信息，超出部分将另行征得您的单独同意：</p>
        <div className="mt-2 overflow-hidden rounded-[10px] border border-border-gold">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#3a0a0a]/70 text-gold-light">
              <tr>
                <th className="px-2 py-1.5">类别</th>
                <th className="px-2 py-1.5">字段</th>
                <th className="px-2 py-1.5">目的</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              <tr>
                <td className="px-2 py-2">身份与生辰</td>
                <td className="px-2 py-2">姓名/昵称、出生日期、时辰、历法、关注重点</td>
                <td className="px-2 py-2">生成八字命盘及预览报告（<span className="font-semibold text-gold">生辰属敏感个人信息</span>）</td>
              </tr>
              <tr>
                <td className="px-2 py-2">订单与交易</td>
                <td className="px-2 py-2">profileId、订单号、金额、支付方式</td>
                <td className="px-2 py-2">创建订单、核验金额、交付报告</td>
              </tr>
              <tr>
                <td className="px-2 py-2">网络与设备</td>
                <td className="px-2 py-2">IP、User-Agent、投放归因参数</td>
                <td className="px-2 py-2">风控与归因统计</td>
              </tr>
              <tr>
                <td className="px-2 py-2">客服交付</td>
                <td className="px-2 py-2">订单号关联的企微外部联系人标识</td>
                <td className="px-2 py-2">人工交付完整报告（仅您主动扫码后产生）</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="mb-2 font-kai text-[15px] font-bold text-gold-light">二、存储与保护</h3>
        <ul className="list-disc space-y-1 pl-5">
          <li>存储地域：中国大陆境内，不涉及跨境传输。</li>
          <li>加密存储：生辰、时辰及命理因子以 <span className="text-gold">AES-256-GCM</span> 密文存储，密钥与业务库分离；前端一律脱敏展示。</li>
          <li>传输加密：全程 HTTPS。</li>
          <li>
            保留期限：未付费测算记录 <span className="font-semibold text-gold-light">30 天</span>后匿名化/删除；已付费订单关联记录{' '}
            <span className="font-semibold text-gold-light">1 年</span>后匿名化/删除（便于重复查看及客服核验）。
          </li>
        </ul>
      </section>

      <section>
        <h3 className="mb-2 font-kai text-[15px] font-bold text-gold-light">三、共享清单</h3>
        <p className="mb-2">我们不会向任何第三方出售您的个人信息，仅在以下必要情形共享：</p>
        <div className="overflow-hidden rounded-[10px] border border-border-gold">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#3a0a0a]/70 text-gold-light">
              <tr>
                <th className="px-2 py-1.5">接收方</th>
                <th className="px-2 py-1.5">信息</th>
                <th className="px-2 py-1.5">目的</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              <tr>
                <td className="px-2 py-2">微信支付（财付通）</td>
                <td className="px-2 py-2">订单号、金额、支付类型、客户端 IP</td>
                <td className="px-2 py-2">完成支付及结果核验</td>
              </tr>
              <tr>
                <td className="px-2 py-2">企业微信</td>
                <td className="px-2 py-2">订单号（活码 state）、外部联系人标识</td>
                <td className="px-2 py-2">生成专属客服活码、人工交付</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="mb-2 font-kai text-[15px] font-bold text-gold-light">四、您的权利</h3>
        <p>
          您可通过客服邮箱 <a href={`mailto:${CONTACT_EMAIL}`} className="text-gold underline decoration-gold/40 underline-offset-2">{CONTACT_EMAIL}</a>{' '}
          行使查阅、复制、更正、删除、撤回同意等权利，我们将在 15 个工作日内答复。删除权由客服核验身份后通过后台接口执行。
        </p>
      </section>

      <section>
        <h3 className="mb-2 font-kai text-[15px] font-bold text-gold-light">五、未成年人保护</h3>
        <p>本服务面向成年人。不满 14 周岁儿童请在监护人陪同并取得同意后使用；我们不会主动向未成年人营销。</p>
      </section>

      <section>
        <h3 className="mb-2 font-kai text-[15px] font-bold text-gold-light">六、Cookie 与本地存储</h3>
        <p>仅使用必要的 sessionStorage 缓存最近一次预览报告标题（关闭页面即失效），不使用第三方追踪 Cookie。</p>
      </section>

      <section>
        <h3 className="mb-2 font-kai text-[15px] font-bold text-gold-light">七、政策更新</h3>
        <p>重大变更将在 H5 内显著提示并重新征得同意。您可通过页脚“隐私政策”随时查阅当前版本。</p>
      </section>

      <section className="rounded-[12px] border border-border-gold bg-[#3a0a0a]/40 p-4 text-xs">
        <h4 className="mb-2 font-semibold text-gold-light">八、如何联系我们</h4>
        <p>运营主体：{COMPANY_NAME}</p>
        <p>地址：{CONTACT_ADDRESS}</p>
        <p>
          客服邮箱：<a href={`mailto:${CONTACT_EMAIL}`} className="text-gold underline decoration-gold/40 underline-offset-2">{CONTACT_EMAIL}</a>
        </p>
        <p>备案号：{ICP_NO}</p>
        <p className="mt-2 text-muted">如您认为处理未满足法律要求，也可向网信、公安或市场监管部门投诉举报。</p>
      </section>
    </article>
  )
}
