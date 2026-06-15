import { Button, Dialog, DialogActions, DialogContent, DialogTitle } from "@mui/material";

const LINKS = [
  {
    label: "维护者",
    value: "Troverld@github.com",
    href: "https://github.com/Troverld",
  },
  {
    label: "GitHub 仓库",
    value: "https://github.com/Troverld/auto-sekai-retriever",
    href: "https://github.com/Troverld/auto-sekai-retriever",
  },
  {
    label: "fork 的原始仓库",
    value: "https://github.com/TheOriginalAyaka/sekai-stickers",
    href: "https://github.com/TheOriginalAyaka/sekai-stickers",
  },
  {
    label: "参考的另一个 fork 网站",
    value: "https://st.3kn.jp/",
    href: "https://st.3kn.jp/",
  },
  {
    label: "表情包获取来源",
    value: "https://pjsk.moe",
    href: "https://pjsk.moe",
  },
];

export default function Info({ open, handleClose }) {
  return (
    <Dialog
      open={open}
      onClose={handleClose}
      aria-labelledby="project-info-title"
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle id="project-info-title">项目说明</DialogTitle>
      <DialogContent dividers>
        <div className="info-content">
          {LINKS.map((item) => (
            <p key={item.label} className="info-line">
              <strong>{item.label}：</strong>
              <a href={item.href} target="_blank" rel="noreferrer">
                {item.value}
              </a>
            </p>
          ))}
          <p className="info-line">
            <strong>免责声明：</strong>
            本项目仅用于学习、研究与交流。如相关内容涉及侵权，请联系维护者处理，收到通知后将第一时间删除相关内容。
          </p>
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} color="secondary" autoFocus>
          关闭
        </Button>
      </DialogActions>
    </Dialog>
  );
}
