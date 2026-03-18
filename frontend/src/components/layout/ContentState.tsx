type ContentStateProps = {
  message: string;
  tone?: 'loading' | 'empty';
};

export default function ContentState({
  message,
  tone = 'empty',
}: ContentStateProps) {
  return <p className={`content-state content-state-${tone}`}>{message}</p>;
}
